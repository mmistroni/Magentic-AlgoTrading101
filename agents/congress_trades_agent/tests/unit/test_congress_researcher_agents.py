import pytest
from unittest.mock import patch
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Import refactored agent directly from the skill module
from congress_trades_agent.skills.congress_researcher.agent import (
    congress_researcher,
)
from congress_trades_agent.schemas import CongressSignalsResponse


def test_congress_researcher_agent_skill_migration():
    """Verifies that CongressResearcher is correctly loaded via the Skills Framework."""
    # 1. Verify agent metadata
    assert isinstance(congress_researcher, LlmAgent)
    assert congress_researcher.name == "CongressResearcher"
    assert congress_researcher.model == "gemini-2.5-flash"
    assert congress_researcher.output_key == "political_context"

    # 2. Verify instruction is dynamically loaded from SKILL.md
    assert congress_researcher.instruction is not None
    assert "Washington Policy Strategist & Congress Scout" in congress_researcher.instruction
    assert "fetch_congress_signals" in congress_researcher.instruction

    # 3. Verify tool attachment
    assert len(congress_researcher.tools) == 1
    tool = congress_researcher.tools[0]
    assert isinstance(tool, FunctionTool)
    # Checks underlying wrapped function name from tools.py
    assert tool.func.__name__ == "fetch_congress_signals"


@patch("congress_trades_agent.skills.congress_researcher.scripts.fetch_congress_data.get_bq_data")
def test_congress_researcher_tool_plumbing(mock_get_bq_data):
    """Verifies tool integration and output parsing without making live BigQuery calls."""
    # Mock return value from BigQuery query script execution
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

    # Extract function from ADK wrapper and execute
    tool_func = congress_researcher.tools[0].func
    result = tool_func(analysis_date="2026-07-01")

    # Assert schema parsing and correctness
    assert isinstance(result, CongressSignalsResponse)
    assert result.count == 1
    assert result.signals[0].ticker == "LMT"
    assert result.signals[0].net_buy_activity == 6
    assert result.signals[0].market_uptrend is True
    mock_get_bq_data.assert_called_once_with("2026-07-01")