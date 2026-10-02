from unittest.mock import MagicMock, patch
import pytest

# Adjust imports to match your actual module paths
from congress_trades_agent.skills.insider_analyst.scripts.lobbying_signals import (
    get_lobbying_data,
)
# Import get_form4_data from its respective module (e.g., form4_signals)
from congress_trades_agent.skills.insider_analyst.scripts.insider_signals import (
    get_form4_data,
)


@patch("congress_trades_agent.skills.insider_analyst.scripts.insider_signals.get_bq_client")
def test_get_form4_data_query_parameters(mock_get_bq_client):
    # 1. Setup mock client and query result
    mock_client = MagicMock()
    mock_get_bq_client.return_value = mock_client

    mock_query_job = MagicMock()
    mock_client.query.return_value = mock_query_job

    # BigQuery row mock with .items() populated
    row_data = {
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
    mock_row = MagicMock()
    mock_row.items.return_value = row_data.items()
    mock_query_job.result.return_value = [mock_row]

    # 2. Invoke script function
    results = get_form4_data(
        analysis_date="2026-03-01", ticker="NVDA", lookback_days=90
    )

    # 3. Assertions
    mock_client.query.assert_called_once()
    _, call_kwargs = mock_client.query.call_args

    job_config = call_kwargs.get("job_config")
    assert job_config is not None

    param_dict = {
        param.name: param.value for param in job_config.query_parameters
    }
    assert param_dict.get("analysis_date") == "2026-03-01"
    assert param_dict.get("ticker") == "NVDA"
    assert param_dict.get("lookback_days") == 90

    assert len(results) == 1
    assert results[0]["ticker"] == "NVDA"


@patch("congress_trades_agent.skills.insider_analyst.scripts.lobbying_signals.get_bq_client")
def test_get_lobbying_data_query_parameters(mock_get_bq_client):
    # 1. Setup mock client and query result
    mock_client = MagicMock()
    mock_get_bq_client.return_value = mock_client

    mock_query_job = MagicMock()
    mock_client.query.return_value = mock_query_job

    # BigQuery row mock with .items() populated
    row_data = {
        "ticker": "AAPL",
        "client_name": "Apple Inc.",
        "key_issues": "CPT, TAX, TRD",
        "current_spend": 1200000.0,
        "prior_spend": 800000.0,
        "spend_growth_pct": 50.0,
    }
    mock_row = MagicMock()
    mock_row.items.return_value = row_data.items()
    mock_query_job.result.return_value = row_data

    # 2. Invoke script function
    results = get_lobbying_data(
        analysis_date="2026-03-01", ticker="AAPL", lookback_days=90
    )

    # 3. Assertions
    mock_client.query.assert_called_once()
    _, call_kwargs = mock_client.query.call_args

    job_config = call_kwargs.get("job_config")
    assert job_config is not None

    param_dict = {
        param.name: param.value for param in job_config.query_parameters
    }
    assert param_dict.get("analysis_date") == "2026-03-01"
    assert param_dict.get("ticker") == "AAPL"
    assert param_dict.get("lookback_days") == 90

    assert len(results) == 1
    assert results[0]["ticker"] == "AAPL"
    assert results[0]["spend_growth_pct"] == 50.0