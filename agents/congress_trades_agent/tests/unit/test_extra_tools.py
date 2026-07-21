import pytest
from unittest.mock import MagicMock, patch
from congress_trades_agent.schemas import Form4SignalResponse
from congress_trades_agent.extra_tools import fetch_form4_signals_tool


@pytest.fixture
def mock_bigquery_client():
    """Fixture to mock the BigQuery client and query execution flow."""
    with patch("congress_trades_agent.extra_tools.bigquery.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client


def create_mock_row(ticker, title, side, shares, filing_date, is_officer=True, is_director=False):
    """
    Helper function to create a mock BigQuery row matching `form4_master` columns.
    Defaults is_officer to True to reflect executive filings.
    """
    return {
        "ticker": ticker,
        "insider_title": title,
        "is_officer": is_officer,
        "is_director": is_director,
        "transaction_type": side,
        "shares": shares,
        "transaction_date": filing_date,
    }


def test_fetch_form4_signals_strong_buy_confluence(mock_bigquery_client):
    """Test CEO open-market purchase triggers 'Strong Buy Confluence'."""
    # Arrange
    mock_job = MagicMock()
    mock_row = MagicMock()
    mock_row.items.return_value = create_mock_row(
        ticker="BE",
        title="CHIEF EXECUTIVE OFFICER",
        side="BUY",
        shares=10000,
        filing_date="2026-06-15",
        is_officer=True,
        is_director=True,
    ).items()
    
    mock_job.result.return_value = [mock_row]
    mock_bigquery_client.query.return_value = mock_job

    # Act
    result = fetch_form4_signals_tool(ticker="BE", analysis_date="2026-07-01")

    # Assert
    assert isinstance(result, Form4SignalResponse)
    assert result.ticker == "BE"
    assert result.signal_strength == "Strong Buy Confluence"
    assert result.transaction_type == "Buy"
    assert result.shares == 10000
    assert result.error is None


def test_fetch_form4_signals_insider_dumping_warning(mock_bigquery_client):
    """Test CFO selling shares triggers 'Warning - Insider Dumping'."""
    # Arrange
    mock_job = MagicMock()
    mock_row = MagicMock()
    mock_row.items.return_value = create_mock_row(
        ticker="MOH",
        title="CHIEF FINANCIAL OFFICER",
        side="SELL",
        shares=5000,
        filing_date="2026-06-20",
        is_officer=True,
        is_director=False,
    ).items()
    
    mock_job.result.return_value = [mock_row]
    mock_bigquery_client.query.return_value = mock_job

    # Act
    result = fetch_form4_signals_tool(ticker="MOH", analysis_date="2026-07-01")

    # Assert
    assert isinstance(result, Form4SignalResponse)
    assert result.ticker == "MOH"
    assert result.signal_strength == "Warning - Insider Dumping"
    assert result.transaction_type == "Sell"
    assert result.error is None


def test_fetch_form4_signals_no_records_found(mock_bigquery_client):
    """Test behavior when BigQuery returns empty results."""
    # Arrange
    mock_job = MagicMock()
    mock_job.result.return_value = []  # Empty results list
    mock_bigquery_client.query.return_value = mock_job

    # Act
    result = fetch_form4_signals_tool(ticker="NVDA", analysis_date="2026-07-01")

    # Assert
    assert isinstance(result, Form4SignalResponse)
    assert result.ticker == "NVDA"
    assert result.signal_strength == "Neutral"
    assert result.error == "No recent insider transactions found."


def test_fetch_form4_signals_bigquery_exception_handling(mock_bigquery_client):
    """Test graceful handling when BigQuery throws a runtime error or permission error."""
    # Arrange
    mock_bigquery_client.query.side_effect = Exception("BigQuery Access Denied")

    # Act
    result = fetch_form4_signals_tool(ticker="AAPL", analysis_date="2026-07-01")

    # Assert
    assert isinstance(result, Form4SignalResponse)
    assert result.ticker == "AAPL"
    assert result.signal_strength == "Neutral"
    assert "Failed to execute query: BigQuery Access Denied" in result.error