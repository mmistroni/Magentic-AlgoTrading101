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


# Scenario 1: Multi-Ticker High Conviction Cluster
@patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_data")
def test_scenario_multi_ticker_conviction(mock_get_bq_data):
    """Scenario: Multiple tickers show strong congressional accumulation in a market uptrend."""
    mock_get_bq_data.return_value = [
        {
            "signal_date": "2026-07-01",
            "ticker": "LMT",
            "purchase_count": 5,
            "sale_count": 0,
            "net_buy_activity": 5,
            "buying_days_count": 3,
            "last_trade_date": "2026-06-28",
            "market_uptrend": True,
        },
        {
            "signal_date": "2026-07-01",
            "ticker": "NOC",
            "purchase_count": 4,
            "sale_count": 0,
            "net_buy_activity": 4,
            "buying_days_count": 2,
            "last_trade_date": "2026-06-29",
            "market_uptrend": True,
        },
    ]

    tool_func = congress_researcher.tools[0].func
    result = tool_func(analysis_date="2026-07-01")

    assert isinstance(result, CongressSignalsResponse)
    assert result.count == 2
    assert result.error is None
    tickers = [s.ticker for s in result.signals]
    assert "LMT" in tickers and "NOC" in tickers


# Scenario 2: Market Downtrend Warning
@patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_data")
def test_scenario_market_downtrend(mock_get_bq_data):
    """Scenario: Congressional buying occurs while market regime is in a downtrend (market_uptrend = False)."""
    mock_get_bq_data.return_value = [
        {
            "signal_date": "2026-07-01",
            "ticker": "NVDA",
            "purchase_count": 3,
            "sale_count": 1,
            "net_buy_activity": 2,
            "buying_days_count": 1,
            "last_trade_date": "2026-06-30",
            "market_uptrend": False,
        }
    ]

    tool_func = congress_researcher.tools[0].func
    result = tool_func(analysis_date="2026-07-01")

    assert result.count == 1
    assert result.signals[0].market_uptrend is False


# Scenario 3: Empty Results / Quiet Market
@patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_data")
def test_scenario_no_signals(mock_get_bq_data):
    """Scenario: BigQuery returns no congressional disclosures for the target date."""
    mock_get_bq_data.return_value = []

    tool_func = congress_researcher.tools[0].func
    result = tool_func(analysis_date="2026-07-01")

    assert isinstance(result, CongressSignalsResponse)
    assert result.count == 0
    assert len(result.signals) == 0
    assert result.error is None


# Scenario 4: Query Exception / BigQuery Outage
@patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_data")
def test_scenario_bigquery_error(mock_get_bq_data):
    """Scenario: Database connection or SQL query raises an exception."""
    mock_get_bq_data.side_effect = Exception("BigQuery Connection Timeout")

    tool_func = congress_researcher.tools[0].func
    result = tool_func(analysis_date="2026-07-01")

    assert isinstance(result, CongressSignalsResponse)
    assert result.count == 0
    assert result.signals == []
    assert "BigQuery Connection Timeout" in result.error