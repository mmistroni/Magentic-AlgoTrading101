import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from congress_trades_agent.skills.congress_trader.agent import (
    congress_trader,
    parse_skill_instructions,
    SKILL_DIR
)
from congress_trades_agent.skills.congress_trader.tools import (
    get_fundamentals,
    fetch_historical_episodes,
    store_trade_decision
)


def test_congress_trader_agent_structure_and_hierarchy():
    """Verify LlmAgent structure, model configuration, skill instruction loading, and tool bindings."""
    assert isinstance(congress_trader, LlmAgent)
    assert congress_trader.name == "CongressTrader"
    assert congress_trader.model == "gemini-3.5-flash"
    
    # Verify instructions were successfully loaded from SKILL.md and frontmatter stripped
    assert isinstance(congress_trader.instruction, str)
    assert len(congress_trader.instruction) > 0
    assert not congress_trader.instruction.startswith("---")
    assert "CongressTrader Playbook" in congress_trader.instruction

    # Verify all core tools are bound to the agent instance
    registered_tools = {t.func if isinstance(t, FunctionTool) else t for t in congress_trader.tools}
    # agent.py registers fetch_fmp_fundamentals
    from congress_trades_agent.skills.congress_trader.tools import fetch_fmp_fundamentals
    assert fetch_fmp_fundamentals in registered_tools
    assert fetch_historical_episodes in registered_tools
    assert store_trade_decision in registered_tools


def test_parse_skill_instructions_utility():
    """Verify that SKILL.md frontmatter parser correctly strips YAML frontmatter."""
    instructions = parse_skill_instructions(SKILL_DIR)
    assert isinstance(instructions, str)
    assert len(instructions) > 0
    assert not instructions.startswith("---")


@patch("congress_trades_agent.skills.congress_trader.tools.fetch_fmp_fundamentals")
@patch("congress_trades_agent.skills.congress_trader.tools.execute_fetch_decisions")
@patch("congress_trades_agent.skills.congress_trader.tools.execute_store_decision")
def test_congress_trader_tool_implementations(mock_execute_store, mock_execute_fetch, mock_fetch_fmp):
    """Test actual underlying tool execution logic (fundamentals, history, and Pydantic validation storage)."""
    
    # Setup mocks
    mock_fetch_fmp.return_value = {
        "ticker": "NVDA",
        "pe_ratio": 31.2,
        "valuation_verdict": "UNDERVALUED",
        "fundamental_health_score": 85.0
    }
    
    mock_row = MagicMock()
    mock_row.decision_id = "dec-NVDA-101"
    mock_row.ticker = "NVDA"
    mock_row.decision_timestamp = "2026-10-29T12:00:00Z"
    mock_row.action = "BUY"
    mock_row.conviction_score = 85.0
    mock_row.decision_snapshot = '{"ticker": "NVDA"}'
    mock_execute_fetch.return_value = [mock_row]
    
    mock_execute_store.return_value = None

    # Test 1: get_fundamentals wrapper calls fetch_fmp_fundamentals and returns Pydantic model
    fund_res = get_fundamentals("nvda")
    assert fund_res.ticker == "NVDA"
    assert fund_res.pe_ratio == 31.2
    assert fund_res.valuation_verdict == "UNDERVALUED"

    # Test 2: fetch_historical_episodes tool wrapper
    history_res = fetch_historical_episodes(ticker="NVDA", min_conviction=80.0)
    assert isinstance(history_res, list)
    assert len(history_res) == 1
    assert history_res[0]["ticker"] == "NVDA"
    assert history_res[0]["action"] == "BUY"

    # Test 3: store_trade_decision tool wrapper (validates via Pydantic & embeds default weights)
    store_res = store_trade_decision(
        ticker="nvda",
        action="BUY",
        conviction_score=82.5,
        pe_ratio=31.2,
        valuation_verdict="UNDERVALUED",
        fundamental_health_score=85.0,
        congressional_net_buys=2,
        insider_cluster_buy=True,
        synthesis_summary="Bullish institutional flow and strong fundamentals."
    )

    assert "Successfully validated and stored decision record" in store_res
    mock_execute_store.assert_called_once()
    
    # Verify default weights applied by Pydantic schema made it into the BigQuery payload
    _, kwargs = mock_execute_store.call_args
    assert kwargs["ticker"] == "NVDA"
    assert kwargs["action"] == "BUY"
    assert "weights_applied" in kwargs["decision_snapshot_json"]