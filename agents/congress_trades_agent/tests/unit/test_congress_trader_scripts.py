import os
from unittest.mock import patch, MagicMock
import pytest

from congress_trades_agent.skills.congress_trader.scripts.fundamentals import \
    fetch_fmp_fundamentals

from congress_trades_agent.skills.congress_trader.scripts.sql_executor import (
    execute_store_decision,
    execute_fetch_decisions
)


@patch("congress_trades_agent.skills.congress_trader.scripts.fundamentals.requests.get")
def test_fetch_fmp_fundamentals_success(mock_get, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "fake_key")
    
    # Mock responses for key-metrics-ttm and ratios-ttm
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
        def json(self):
            return self.json_data

    # Side effect to handle multiple calls to different endpoints
    def side_effect(url, timeout=10):
        if "key-metrics-ttm" in url:
            return MockResponse([{"peRatioTTM": 12.5, "freeCashFlowYieldTTM": 0.08}], 200)
        elif "ratios-ttm" in url:
            return MockResponse([{"debtToEquityRatioTTM": 0.5}], 200)
        return MockResponse([], 404)

    mock_get.side_effect = side_effect

    result = fetch_fmp_fundamentals("AAPL")
    
    assert result["ticker"] == "AAPL"
    assert result["pe_ratio"] == 12.5
    assert result["debt_to_equity"] == 0.5
    assert result["valuation_verdict"] == "UNDERVALUED"
    assert result["fundamental_health_score"] > 50.0
    assert result.get("error") is None

def test_fetch_fmp_fundamentals_missing_key(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    result = fetch_fmp_fundamentals("AAPL")
    assert result["error"] == "FMP_API_KEY environment variable is missing."

@patch("congress_trades_agent.skills.congress_trader.scripts.sql_executor.get_bq_client")
def test_execute_store_decision_success(mock_bq_client):
    """Test that execute_store_decision correctly compiles the query and triggers BigQuery execution."""
    mock_query_job = MagicMock()
    mock_bq_client.query.return_value = mock_query_job

    decision_id = "dec-uuid-001"
    ticker = "MSFT"
    timestamp = "2026-10-20T12:00:00Z"
    action = "BUY"
    conviction = 82.5
    snapshot_json = '{"ticker": "MSFT", "action": "BUY"}'

    execute_store_decision(
        decision_id=decision_id,
        ticker=ticker,
        decision_timestamp=timestamp,
        action=action,
        conviction_score=conviction,
        decision_snapshot_json=snapshot_json
    )

    # Verify BigQuery client was called and job result was awaited
    mock_bq_client.query.assert_called_once()
    mock_query_job.result.assert_called_once()

    # Validate query parameters passed to BigQuery configuration
    _, called_kwargs = mock_bq_client.query.call_args
    job_config = called_kwargs.get("job_config")
    assert job_config is not None
    
    param_dict = {p.name: p.value for p in job_config.query_parameters}
    assert param_dict["decision_id"] == decision_id
    assert param_dict["ticker"] == "MSFT"  # Should be uppercase
    assert param_dict["action"] == "BUY"
    assert param_dict["conviction_score"] == 82.5
    assert param_dict["decision_snapshot_json"] == snapshot_json


@patch("congress_trades_agent.skills.congress_trader.scripts.sql_executor.get_bq_client")
def test_execute_fetch_decisions_with_filters(mock_get_bq_client):
    """Test that execute_fetch_decisions properly binds lookup filters and limits."""
    # 1. Get the mock client instance
    mock_bq_client = mock_get_bq_client.return_value

    # 2. Setup the mock query job and its result iterator
    mock_query_job = MagicMock()
    mock_iterator = MagicMock()
    
    # Crucial: wire .result() to return our mock iterator
    mock_query_job.result.return_value = mock_iterator
    
    # Crucial: wire client.query(...) to return our mock query job
    mock_bq_client.query.return_value = mock_query_job

    # 3. Execute the function
    result_iterator = execute_fetch_decisions(
        ticker="nvda",
        valuation_verdict="undervalued",
        min_conviction=75.0,
        limit=5
    )

    # 4. Assertions
    assert result_iterator == mock_iterator
    mock_bq_client.query.assert_called_once()
    mock_query_job.result.assert_called_once()

    # Validate parameters are normalized and bound correctly
    _, called_kwargs = mock_bq_client.query.call_args
    job_config = called_kwargs.get("job_config")
    assert job_config is not None

    param_dict = {p.name: p.value for p in job_config.query_parameters}
    assert param_dict["ticker"] == "NVDA"
    assert param_dict["val_verdict"] == "UNDERVALUED"
    assert param_dict["min_conviction"] == 75.0
    assert param_dict["limit"] == 5