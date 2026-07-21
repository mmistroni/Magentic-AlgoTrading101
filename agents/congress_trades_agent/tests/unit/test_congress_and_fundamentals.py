import pytest
import pandas as pd
from unittest.mock import MagicMock, patch

from congress_trades_agent.schemas import (
    CongressSignalsResponse,
    FundamentalsResponse,
)
from congress_trades_agent.tools import (
    fetch_congress_signals_tool,
    check_fundamentals_tool,
)


# ==============================================================================
# FIXTURES
# ==============================================================================

@pytest.fixture
def mock_bigquery_client():
    """Fixture to mock google.cloud.bigquery.Client."""
    with patch("congress_trades_agent.tools.bigquery.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client


@pytest.fixture
def mock_yf_ticker():
    """Fixture to mock yfinance.Ticker."""
    with patch("congress_trades_agent.tools.yf.Ticker") as mock_ticker:
        yield mock_ticker


# ==============================================================================
# TESTS FOR fetch_congress_signals_tool
# ==============================================================================

@patch("congress_trades_agent.tools._get_spy_data")
def test_fetch_congress_signals_success(mock_spy_data, mock_bigquery_client):
    """Test retrieving high conviction signals when BigQuery returns valid rows."""
    # Mock SPY Data to return an empty DataFrame so market_regime defaults to True (Bull)
    mock_spy_data.return_value = pd.DataFrame()

    # Mock DataFrame returned by BigQuery query job
    mock_df = pd.DataFrame([
        {
            "signal_date": "2026-07-01",
            "ticker": "LMT",
            "purchase_count": 6,
            "sale_count": 0,
            "net_buy_activity": 6,
            "buying_days_count": 3,
            "last_trade_date": "2026-06-28",
        },
        {
            "signal_date": "2026-07-01",
            "ticker": "NVDA",
            "purchase_count": 8,
            "sale_count": 0,
            "net_buy_activity": 8,
            "buying_days_count": 4,
            "last_trade_date": "2026-06-29",
        }
    ])
    
    mock_query_job = MagicMock()
    mock_query_job.to_dataframe.return_value = mock_df
    mock_bigquery_client.query.return_value = mock_query_job

    # Act
    result = fetch_congress_signals_tool(analysis_date="2026-07-01")

    # Assert
    assert isinstance(result, CongressSignalsResponse)
    assert result.analysis_date == "2026-07-01"
    assert result.count == 2
    assert result.signals[0].ticker == "LMT"
    assert result.signals[0].net_buy_activity == 6
    assert result.signals[0].market_uptrend is True
    assert result.signals[1].ticker == "NVDA"
    assert result.error is None


def test_fetch_congress_signals_empty_results(mock_bigquery_client):
    """Test behavior when BigQuery query returns an empty dataframe."""
    # Arrange
    mock_query_job = MagicMock()
    mock_query_job.to_dataframe.return_value = pd.DataFrame()
    mock_bigquery_client.query.return_value = mock_query_job

    # Act
    result = fetch_congress_signals_tool(analysis_date="2026-07-01")

    # Assert
    assert isinstance(result, CongressSignalsResponse)
    assert result.count == 0
    assert result.signals == []
    assert result.error is None


def test_fetch_congress_signals_exception_handling(mock_bigquery_client):
    """Test graceful error handling when BigQuery raises a connection failure."""
    # Arrange
    mock_bigquery_client.query.side_effect = Exception("BigQuery Access Denied")

    # Act
    result = fetch_congress_signals_tool(analysis_date="2026-07-01")

    # Assert
    assert isinstance(result, CongressSignalsResponse)
    assert result.count == 0
    assert result.signals == []
    assert "BigQuery Access Denied" in result.error


# ==============================================================================
# TESTS FOR check_fundamentals_tool
# ==============================================================================

def test_check_fundamentals_success(mock_yf_ticker):
    """Test check_fundamentals_tool correctly parses stock info metrics."""
    # Arrange
    mock_stock = MagicMock()
    mock_stock.info = {
        "sector": "Technology",
        "industry": "Semiconductors",
        "marketCap": 2_500_000_000_000,  # $2,500 Billion
        "beta": 1.68,
        "forwardPE": 32.5,
        "debtToEquity": 45.2,
        "dividendYield": 0.0015,
    }
    mock_yf_ticker.return_value = mock_stock

    # Act
    result = check_fundamentals_tool(ticker="NVDA")

    # Assert
    assert isinstance(result, FundamentalsResponse)
    assert result.ticker == "NVDA"
    assert result.sector == "Technology"
    assert result.industry == "Semiconductors"
    assert result.market_cap_B == 2500.0
    assert result.beta == 1.68
    assert result.forward_pe == 32.5
    assert result.debt_to_equity == 45.2
    assert result.dividend_yield == 0.0015
    assert result.error is None


def test_check_fundamentals_missing_optional_fields(mock_yf_ticker):
    """Test fallback defaults when yfinance info dictionary is missing optional keys."""
    # Arrange
    mock_stock = MagicMock()
    mock_stock.info = {
        "sector": "Aerospace & Defense",
        "marketCap": 110_000_000_000,  # $110 Billion
    }
    mock_yf_ticker.return_value = mock_stock

    # Act
    result = check_fundamentals_tool(ticker="LMT")

    # Assert
    assert isinstance(result, FundamentalsResponse)
    assert result.ticker == "LMT"
    assert result.sector == "Aerospace & Defense"
    assert result.industry == "Unknown"
    assert result.market_cap_B == 110.0
    assert result.beta == 1.0          # Fallback default
    assert result.forward_pe == 0.0    # Fallback default
    assert result.debt_to_equity is None
    assert result.dividend_yield == 0.0
    assert result.error is None


def test_check_fundamentals_exception_handling(mock_yf_ticker):
    """Test graceful failure handling when yfinance throws an exception."""
    # Arrange
    mock_yf_ticker.side_effect = Exception("yfinance Rate Limit Exceeded")

    # Act
    result = check_fundamentals_tool(ticker="FAIL")

    # Assert
    assert isinstance(result, FundamentalsResponse)
    assert result.ticker == "FAIL"
    assert result.sector == "Unknown"
    assert result.error == "Data Unavailable"