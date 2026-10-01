from unittest.mock import patch

from congress_trades_agent.skills.insider_analyst.tools import (
    fetch_form4_signals_tool,
    fetch_lobbying_signals_tool,
)
from congress_trades_agent.schemas import (
    Form4SignalsResponse,
    LobbyingSignalsResponse,
)


@patch("congress_trades_agent.skills.insider_analyst.tools.get_form4_data")
def test_fetch_form4_signals_tool_success(mock_get_form4):
    # 1. Setup mock BigQuery script response
    mock_get_form4.return_value = [
        {
            "ticker": "NVDA",
            "issuer": "NVIDIA Corp",
            "net_buy_value": 500000.0,
            "unique_buyers": 3,
            "is_c_suite_buy": True,
            "is_cluster_buy": True,
            "buy_count": 3,
            "sell_count": 0,
            "insider_activity_score": 65.0,
        }
    ]

    # 2. Invoke tool wrapper function
    response = fetch_form4_signals_tool.func(
        analysis_date="2026-03-01", ticker="NVDA", lookback_days=90
    )

    # 3. Assertions using standard pytest syntax
    mock_get_form4.assert_called_once_with(
        analysis_date="2026-03-01", ticker="NVDA", lookback_days=90
    )
    assert isinstance(response, Form4SignalsResponse)
    assert response.analysis_date == "2026-03-01"
    assert response.count == 1
    assert response.error is None
    assert response.signals[0].ticker == "NVDA"
    assert response.signals[0].is_cluster_buy is True


@patch("congress_trades_agent.skills.insider_analyst.tools.get_form4_data")
def test_fetch_form4_signals_tool_error_handling(mock_get_form4):
    # 1. Simulate database failure
    mock_get_form4.side_effect = Exception("BigQuery Connection Timeout")

    # 2. Execute tool
    response = fetch_form4_signals_tool.func(
        analysis_date="2026-03-01", ticker="NVDA"
    )

    # 3. Verify graceful error packaging
    assert isinstance(response, Form4SignalsResponse)
    assert response.count == 0
    assert "BigQuery Connection Timeout" in response.error


@patch("congress_trades_agent.skills.insider_analyst.tools.get_lobbying_data")
def test_fetch_lobbying_signals_tool_success(mock_get_lobbying):
    # 1. Setup mock response
    mock_get_lobbying.return_value = [
        {
            "ticker": "AAPL",
            "client_name": "Apple Inc.",
            "key_issues": "CPT, TAX, TRD",
            "current_spend": 1200000.0,
            "prior_spend": 800000.0,
            "spend_growth_pct": 50.0,
        }
    ]

    # 2. Invoke tool
    response = fetch_lobbying_signals_tool.func(
        analysis_date="2026-03-01", ticker="AAPL", lookback_days=90
    )

    # 3. Assertions
    mock_get_lobbying.assert_called_once_with(
        analysis_date="2026-03-01", ticker="AAPL", lookback_days=90
    )
    assert isinstance(response, LobbyingSignalsResponse)
    assert response.analysis_date == "2026-03-01"
    assert response.count == 1
    assert response.error is None
    assert response.signals[0].ticker == "AAPL"
    assert response.signals[0].spend_growth_pct == 50.0


@patch("congress_trades_agent.skills.insider_analyst.tools.get_lobbying_data")
def test_fetch_lobbying_signals_tool_error_handling(mock_get_lobbying):
    # 1. Simulate failure
    mock_get_lobbying.side_effect = Exception("Table not found")

    # 2. Execute tool
    response = fetch_lobbying_signals_tool.func(analysis_date="2026-03-01")

    # 3. Assertions
    assert isinstance(response, LobbyingSignalsResponse)
    assert response.count == 0
    assert "Table not found" in response.error