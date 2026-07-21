import pytest
from unittest.mock import MagicMock, patch
from congress_trades_agent.schemas import LobbyingSignalResponse
from congress_trades_agent.extra_tools import fetch_lobbying_signals_tool


@pytest.fixture
def mock_bigquery_client():
    """Fixture to mock BigQuery Client for lobbying queries."""
    with patch("congress_trades_agent.extra_tools.bigquery.Client") as mock_client_cls:
        mock_client = MagicMock()
        mock_client_cls.return_value = mock_client
        yield mock_client


def test_fetch_lobbying_signals_success(mock_bigquery_client):
    """Test retrieving active lobbying data with issues parsed into a list."""
    # Arrange
    mock_job = MagicMock()
    mock_row = MagicMock()
    mock_row.items.return_value = {
        "ticker": "NVDA",
        "client_name": "NVIDIA CORPORATION",
        "total_spend": 2400000.0,
        "latest_filing": "2026-05-10",
        "raw_issues": "CHIPS Act | Artificial Intelligence | Export Controls",
        "number_of_filings": 4,
    }.items()

    mock_job.result.return_value = [mock_row]
    mock_bigquery_client.query.return_value = mock_job

    # Act
    result = fetch_lobbying_signals_tool(ticker="NVDA", analysis_date="2026-07-01")

    # Assert
    assert isinstance(result, LobbyingSignalResponse)
    assert result.ticker == "NVDA"
    assert result.company_name == "NVIDIA CORPORATION"
    assert result.total_spend_last_12m == 2400000.0
    assert result.number_of_filings == 4
    assert len(result.top_lobbied_issues) == 3
    assert "Artificial Intelligence" in result.top_lobbied_issues
    assert result.lobbying_status == "Active Lobbying Detected"
    assert result.error is None


def test_fetch_lobbying_signals_no_activity(mock_bigquery_client):
    """Test behavior when no lobbying activity is found for a ticker."""
    # Arrange
    mock_job = MagicMock()
    mock_job.result.return_value = []  # Empty results list
    mock_bigquery_client.query.return_value = mock_job

    # Act
    result = fetch_lobbying_signals_tool(ticker="SMALL", analysis_date="2026-07-01")

    # Assert
    assert isinstance(result, LobbyingSignalResponse)
    assert result.ticker == "SMALL"
    assert result.lobbying_status == "No recent lobbying activity found."
    assert result.total_spend_last_12m == 0.0
    assert result.top_lobbied_issues == []
    assert result.error is None


def test_fetch_lobbying_signals_database_error(mock_bigquery_client):
    """Test graceful failure when BigQuery raises an exception."""
    # Arrange
    mock_bigquery_client.query.side_effect = Exception("Connection Timeout")

    # Act
    result = fetch_lobbying_signals_tool(ticker="FAIL")

    # Assert
    assert isinstance(result, LobbyingSignalResponse)
    assert result.ticker == "FAIL"
    assert result.lobbying_status == "Error"
    assert "Database error: Connection Timeout" in result.error