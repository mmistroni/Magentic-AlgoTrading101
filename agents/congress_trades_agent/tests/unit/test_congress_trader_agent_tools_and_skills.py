import pytest
from pathlib import Path
from unittest.mock import patch, MagicMock

from congress_trades_agent.skills.congress_trader.agent import (
    congress_trader,
    parse_skill_instructions,
    SKILL_DIR
)
from congress_trades_agent.skills.congress_trader.tools import (
    fetch_fmp_fundamentals,
    store_trade_decision,
    fetch_historical_episodes
)

def test_parse_skill_instructions_strips_frontmatter():
    """Ensure SKILL.md frontmatter is correctly stripped and instructions are extracted."""
    instructions = parse_skill_instructions(SKILL_DIR)
    assert isinstance(instructions, str)
    assert len(instructions) > 0
    assert not instructions.startswith("---")


def test_congress_trader_agent_tool_bindings():
    """Verify the LlmAgent is bound to all required tools and configuration parameters."""
    assert congress_trader.name == "CongressTrader"
    assert congress_trader.model == "gemini-3.5-flash"
    
    registered_tools = list(congress_trader.tools)
    assert fetch_fmp_fundamentals in registered_tools
    assert store_trade_decision in registered_tools
    assert fetch_historical_episodes in registered_tools

@patch("congress_trades_agent.skills.congress_trader.tools.execute_store_decision")
def test_store_trade_decision_tool_integration(mock_execute_store):
    """Test that store_trade_decision correctly builds the Pydantic model, serializes JSON, and calls the SQL executor."""
    mock_execute_store.return_value = None

    result = store_trade_decision(
        ticker="nvda",
        action="BUY",
        conviction_score=82.5,
        pe_ratio=31.2,
        valuation_verdict="UNDERVALUED",
        fundamental_health_score=85.0,
        congressional_net_buys=2,
        insider_cluster_buy=True,
        price=138.50,  # <-- Added price parameter!
        synthesis_summary="Bullish institutional flow and strong fundamentals."
    )

    assert "Successfully validated and stored decision record" in result
    mock_execute_store.assert_called_once()
    
    # Verify that the executor received the serialized JSON snapshot and entry price
    _, kwargs = mock_execute_store.call_args
    assert kwargs["ticker"] == "NVDA"
    assert kwargs["action"] == "BUY"
    assert kwargs["conviction_score"] == 82.5
    assert kwargs["entry_price"] == 138.50  # <-- Verify entry_price is passed to SQL executor
    assert "decision_snapshot_json" in kwargs
    
    # Optional: ensure the default weights were embedded in the serialized snapshot JSON
    assert "weights_applied" in kwargs["decision_snapshot_json"]


@patch("congress_trades_agent.skills.congress_trader.tools.execute_fetch_decisions")
def test_fetch_historical_episodes_tool_integration(mock_execute_fetch):
    """Test that fetch_historical_episodes correctly unpacks rows from the SQL executor."""
    mock_row = MagicMock()
    mock_row.decision_id = "dec-test-123"
    mock_row.ticker = "NVDA"
    mock_row.decision_timestamp = "2026-10-21T12:00:00Z"
    mock_row.action = "BUY"
    mock_row.conviction_score = 90.0
    mock_row.decision_snapshot = {"ticker": "NVDA", "fundamentals": {"pe_ratio": 31.2}}


    mock_execute_fetch.return_value = [mock_row]

    results = fetch_historical_episodes(
        ticker="nvda",
        valuation_verdict="UNDERVALUED",
        min_conviction=80.0,
        limit=5
    )

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["ticker"] == "NVDA"
    assert results[0]["decision_snapshot"]["fundamentals"]["pe_ratio"] == 31.2
    mock_execute_fetch.assert_called_once()