import pytest
import pandas as pd
from unittest.mock import patch
from congress_trades_agent.skills.congress_researcher.scripts.market_regime import (
    check_market_regime,
)


@pytest.fixture
def mock_uptrend_df():
    df = pd.DataFrame(
        {
            "date": [pd.to_datetime("2026-06-15")],
            "adjClose": [550.0],
            "SMA200": [500.0],
        }
    )
    df.set_index("date", inplace=True)
    return df


@pytest.fixture
def mock_downtrend_df():
    df = pd.DataFrame(
        {
            "date": [pd.to_datetime("2026-06-15")],
            "adjClose": [450.0],
            "SMA200": [500.0],
        }
    )
    df.set_index("date", inplace=True)
    return df


@patch(
    "congress_trades_agent.skills.congress_researcher.scripts.market_regime._get_spy_data"
)
def test_check_market_regime_uptrend(mock_get_spy_data, mock_uptrend_df):
    """Verifies check_market_regime returns True when SPY is in an uptrend."""
    mock_get_spy_data.return_value = mock_uptrend_df

    result = check_market_regime("2026-06-15", "2026-06-30")

    assert result is True
    # _get_spy_data is called with context_date_str ("2026-06-30")
    mock_get_spy_data.assert_called_once_with("2026-06-30")


@patch(
    "congress_trades_agent.skills.congress_researcher.scripts.market_regime._get_spy_data"
)
def test_check_market_regime_downtrend(mock_get_spy_data, mock_downtrend_df):
    """Verifies check_market_regime returns False when SPY is in a downtrend."""
    mock_get_spy_data.return_value = mock_downtrend_df

    result = check_market_regime(
        row_date="2026-06-15", context_date_str="2026-06-30"
    )

    assert result is False
    mock_get_spy_data.assert_called_once_with("2026-06-30")


@patch(
    "congress_trades_agent.skills.congress_researcher.scripts.market_regime._get_spy_data"
)
def test_check_market_regime_empty_data(mock_get_spy_data):
    """Verifies check_market_regime safely defaults to True when data is missing."""
    mock_get_spy_data.return_value = pd.DataFrame()

    result = check_market_regime("2026-06-15", "2026-06-30")

    assert result is True
    mock_get_spy_data.assert_called_once_with("2026-06-30")