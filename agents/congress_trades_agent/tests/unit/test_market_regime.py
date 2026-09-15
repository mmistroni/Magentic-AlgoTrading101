import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

from congress_trades_agent.skills.congress_researcher.scripts.market_regime import check_market_regime


@pytest.fixture
def mock_uptrend_df():
    """SPY price above 200-day SMA with required date column."""
    return pd.DataFrame([{
        "date": pd.to_datetime("2026-06-15"),
        "adjClose": 550.0,
        "SMA200": 500.0
    }])


@pytest.fixture
def mock_downtrend_df():
    """SPY price below 200-day SMA with required date column."""
    return pd.DataFrame([{
        "date": pd.to_datetime("2026-06-15"),
        "adjClose": 450.0,
        "SMA200": 500.0
    }])


@patch("congress_trades_agent.skills.congress_researcher.scripts.market_regime._get_spy_data")
def test_check_market_regime_uptrend(mock_get_spy_data, mock_uptrend_df):
    """Verifies check_market_regime returns True when SPY is in an uptrend."""
    mock_get_spy_data.return_value = mock_uptrend_df

    result = check_market_regime("2026-06-15", "2026-06-30")

    assert result is True
    mock_get_spy_data.assert_called_once_with("2026-06-15", "2026-06-30")


@patch("congress_trades_agent.skills.congress_researcher.scripts.market_regime._get_spy_data")
def test_check_market_regime_downtrend(mock_get_spy_data, mock_downtrend_df):
    """Verifies check_market_regime returns False when SPY is in a downtrend."""
    mock_get_spy_data.return_value = mock_downtrend_df

    result = check_market_regime(row_date="2026-06-15", context_date_str="2026-06-30")

    assert result is False
    mock_get_spy_data.assert_called_once_with(row_date="2026-06-15", context_date_str="2026-06-30")


@patch("congress_trades_agent.skills.congress_researcher.scripts.market_regime._get_spy_data")
def test_check_market_regime_empty_data(mock_get_spy_data):
    """Verifies fallback behavior when BigQuery returns empty market data."""
    mock_get_spy_data.return_value = pd.DataFrame()
    
    result = check_market_regime("2026-06-15", "2026-06-30")
    assert isinstance(result, bool)