import pytest
from unittest.mock import patch
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

from congress_trades_agent.skills.congress_researcher.agent import congress_researcher
from congress_trades_agent.schemas import CongressSignalsResponse


def test_congress_researcher_agent_skill_migration():
    """Verifies that CongressResearcher loads correctly from the skill directory."""
    assert isinstance(congress_researcher, LlmAgent)
    assert congress_researcher.name == "CongressResearcher"
    assert congress_researcher.output_key == "political_context"

    assert "Washington Policy Strategist & Congress Scout" in congress_researcher.instruction
    assert "fetch_congress_signals(analysis_date)" in congress_researcher.instruction

    assert len(congress_researcher.tools) == 1
    tool = congress_researcher.tools[0]
    assert isinstance(tool, FunctionTool)
    assert tool.func.__name__ == "fetch_congress_signals"


# Target get_bq_data inside tools.py where fetch_congress_signals actually calls it
@patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_data")
def test_congress_researcher_tool_plumbing(mock_get_bq_data):
    """Verifies tool integration and output parsing without making live BigQuery calls."""
    mock_get_bq_data.return_value = [
        {
            "signal_date": "2026-07-01",
            "ticker": "LMT",
            "purchase_count": 6,
            "sale_count": 0,
            "net_buy_activity": 6,
            "buying_days_count": 3,
            "last_trade_date": "2026-06-28",
            "market_uptrend": True,
        }
    ]

    tool_func = congress_researcher.tools[0].func
    result = tool_func(analysis_date="2026-07-01")

    assert isinstance(result, CongressSignalsResponse)
    assert result.count == 1
    assert result.signals[0].ticker == "LMT"
    assert result.signals[0].net_buy_activity == 6
    assert result.signals[0].market_uptrend is True
    mock_get_bq_data.assert_called_once_with("2026-07-01")