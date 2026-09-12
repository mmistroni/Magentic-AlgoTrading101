import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from congress_trades_agent.skills.congress_researcher.scripts.congress_signals import get_bq_data
from congress_trades_agent.skills.congress_researcher.scripts.gov_contracts import get_bq_signals_data

from congress_trades_agent.skills.congress_researcher.tools import (
    fetch_congress_signals,
    fetch_contract_signals,
)
from congress_trades_agent.schemas import CongressSignalsResponse, ContractSignalsResponse


@pytest.fixture
def mock_congress_df():
    return pd.DataFrame([{
        "ticker": "LMT",
        "signal_date": "2026-06-15",
        "purchase_count": 3,
        "sale_count": 0,
        "net_buy_activity": 3,
        "buying_days_count": 2,
        "last_trade_date": "2026-06-20",
    }])


@pytest.fixture
def mock_contracts_df():
    return pd.DataFrame([{
        "action_date": "2026-05-10",
        "recipient_name": "LOCKHEED MARTIN CORP",
        "ticker": "LMT",
        "amount": 75000000.0,
        "agency": "DEPT OF DEFENSE",
        "description": "F-35 Logistics Support",
        "formatted_amount": "$75.0M"
    }])


@patch("google.cloud.bigquery.Client")
@patch("congress_trades_agent.skills.congress_researcher.scripts.congress_signals.check_market_regime")
def test_fetch_congress_signals_end_to_end_wiring(mock_regime, mock_bq_client_cls, mock_congress_df):
    """Verifies: Tool -> Script -> SQL execution -> BQ Parameterized query -> Schema mapping."""
    mock_regime.return_value = True
    
    # Mock BigQuery Client instance and query execution job
    mock_client_instance = MagicMock()
    mock_job = MagicMock()
    mock_job.to_dataframe.return_value = mock_congress_df
    mock_client_instance.query.return_value = mock_job
    mock_bq_client_cls.return_value = mock_client_instance

    # 1. Execute tool call
    analysis_date = "2026-06-30"
    response = fetch_congress_signals(analysis_date=analysis_date)

    # 2. Verify script executed BigQuery query call
    mock_client_instance.query.assert_called_once()
    
    # 3. Verify parameterized query arguments passed to BQ
    _, kwargs = mock_client_instance.query.call_args
    job_config = kwargs.get("job_config")
    assert job_config is not None
    assert len(job_config.query_parameters) == 1
    assert job_config.query_parameters[0].name == "analysis_date"
    assert job_config.query_parameters[0].value == analysis_date

    # 4. Verify end response parsing into Pydantic models
    assert isinstance(response, CongressSignalsResponse)
    assert response.count == 1
    assert response.signals[0].ticker == "LMT"
    assert response.signals[0].market_uptrend is True


@patch("google.cloud.bigquery.Client")
def test_fetch_contract_signals_end_to_end_wiring(mock_bq_client_cls, mock_contracts_df):
    """Verifies: Contract Tool -> Script -> SQL execution -> BQ Parameterized query -> Schema mapping."""
    mock_client_instance = MagicMock()
    mock_job = MagicMock()
    mock_job.to_dataframe.return_value = mock_contracts_df
    mock_client_instance.query.return_value = mock_job
    mock_bq_client_cls.return_value = mock_client_instance

    # 1. Execute tool call
    ticker = "LMT"
    analysis_date = "2026-06-30"
    response = fetch_contract_signals(ticker=ticker, analysis_date=analysis_date)

    # 2. Verify script executed BigQuery query call
    mock_client_instance.query.assert_called_once()

    # 3. Verify parameterized query arguments passed to BQ
    _, kwargs = mock_client_instance.query.call_args
    job_config = kwargs.get("job_config")
    assert job_config is not None
    assert len(job_config.query_parameters) == 2
    
    param_dict = {p.name: p.value for p in job_config.query_parameters}
    assert param_dict["ticker"] == "LMT"
    assert param_dict["analysis_date"] == analysis_date

    # 4. Verify output contracts schema response
    assert isinstance(response, ContractSignalsResponse)
    assert response.ticker == "LMT"
    assert response.total_contract_spend_usd == 75000000.0
    assert response.count == 1
    assert response.signals[0].agency == "DEPT OF DEFENSE"