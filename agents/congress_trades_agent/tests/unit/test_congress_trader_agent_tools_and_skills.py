import json
from unittest.mock import patch, MagicMock
from google.adk.tools import FunctionTool

from congress_trades_agent.skills.congress_trader.agent import (
    congress_trader,
    parse_skill_instructions,
    SKILL_DIR,
)
from congress_trades_agent.skills.congress_trader.tools import (
    get_confluence_report,
    get_fundamentals,
    get_trailing_return,
    store_trade_decision,
    fetch_historical_episodes,
)


def test_parse_skill_instructions_strips_frontmatter():
    """Ensure SKILL.md frontmatter is stripped and key operational rules are present."""
    instructions = parse_skill_instructions(SKILL_DIR)
    assert isinstance(instructions, str)
    assert len(instructions) > 0
    assert not instructions.startswith("---")
    assert "get_confluence_report" in instructions


def test_congress_trader_agent_tool_bindings():
    """Verify the LlmAgent configuration and required tool bindings."""
    assert congress_trader.name == "CongressTrader"
    assert congress_trader.model == "gemini-3.5-flash"

    registered_tools = {
        t.func if isinstance(t, FunctionTool) else t
        for t in congress_trader.tools
    }
    assert get_confluence_report in registered_tools
    assert get_fundamentals in registered_tools
    assert get_trailing_return in registered_tools
    assert store_trade_decision in registered_tools
    assert fetch_historical_episodes in registered_tools


@patch("congress_trades_agent.skills.congress_trader.tools.execute_store_decision")
def test_store_trade_decision_serializes_valid_snapshot(mock_execute_store):
    """Verify store_trade_decision builds a valid Pydantic record and passes serialized JSON."""
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
        price=138.50,
        synthesis_summary="Bullish institutional flow and strong fundamentals.",
    )

    assert "Successfully validated and stored decision record" in result
    mock_execute_store.assert_called_once()

    _, kwargs = mock_execute_store.call_args
    assert kwargs["ticker"] == "NVDA"
    assert kwargs["action"] == "BUY"
    assert kwargs["conviction_score"] == 82.5
    assert kwargs["entry_price"] == 138.50

    snapshot = json.loads(kwargs["decision_snapshot_json"])
    assert snapshot["ticker"] == "NVDA"
    assert "weights_applied" in snapshot
    assert snapshot["signals_aggregated"]["congressional_net_buys"] == 2
    assert snapshot["signals_aggregated"]["insider_cluster_buy"] is True


@patch("congress_trades_agent.skills.congress_trader.tools.execute_fetch_decisions")
def test_fetch_historical_episodes_unpacks_snapshot_json(mock_execute_fetch):
    """Verify fetch_historical_episodes reads decision_snapshot_json properly."""
    mock_row = MagicMock()
    mock_row.decision_id = "dec-test-123"
    mock_row.ticker = "NVDA"
    mock_row.decision_timestamp = "2026-10-21T12:00:00Z"
    mock_row.action = "BUY"
    mock_row.conviction_score = 90.0
    mock_row.decision_snapshot_json = {"ticker": "NVDA", "fundamentals": {"pe_ratio": 31.2}}

    mock_execute_fetch.return_value = [mock_row]

    results = fetch_historical_episodes(
        ticker="nvda",
        valuation_verdict="UNDERVALUED",
        min_conviction=80.0,
        limit=5,
    )

    assert len(results) == 1
    assert results[0]["ticker"] == "NVDA"
    assert results[0]["decision_snapshot"]["fundamentals"]["pe_ratio"] == 31.2
    mock_execute_fetch.assert_called_once()