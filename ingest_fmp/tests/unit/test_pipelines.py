import pytest
from unittest.mock import patch, MagicMock
import pandas as pd

# Import the pipeline functions from your module (adjust module name if needed, e.g., from your_module import ...)
from ingest_fmp.pipeline import (
    get_extra_watchlist,
    run_market_down_pipeline,
    run_high_growth_float_watchlist,
    run_swing_trading_pipeline,
    run_new_highs_pipeline
)

@pytest.fixture
def mock_fmp_environment():
    """Fixture to mock FMPClient, StockScreeners, and all Validators across all pipelines."""
    with patch("ingest_fmp.pipeline.FMPClient") as mock_client_cls, \
         patch("ingest_fmp.pipeline.StockScreeners") as mock_screeners_cls, \
         patch("ingest_fmp.pipeline.FundamentalValidator") as mock_fund_cls, \
         patch("ingest_fmp.pipeline.MarketDownFundamentalValidator") as mock_mdown_fund_cls, \
         patch("ingest_fmp.pipeline.TechnicalValidator") as mock_tech_cls, \
         patch("ingest_fmp.pipeline.BearishTechnicalValidator") as mock_bear_cls:

        # Configure mock screener responses with fields needed for pandas filters
        mock_screeners_instance = mock_screeners_cls.return_value
        mock_screeners_instance.get_base_universe.return_value = [{"symbol": "AAPL"}]
        
        mock_client_instance = mock_client_cls.return_value
        mock_client_instance.get_company_screener.return_value = [
            {
                "symbol": "TEST",
                "companyName": "Test Corp",
                "marketCap": 5000000000,
                "price": 100.0,
                "open": 95.0,
                "previousClose": 94.0,
                "yearHigh": 101.0,
                "relativeVolume": 2.0,
                "floatShares": 20000000,
                "shortFloat": 0.25
            }
        ]

        # Configure all validators to return True (passing checks)
        mock_fund_cls.return_value.evaluate.return_value = True
        mock_mdown_fund_cls.return_value.evaluate.return_value = True
        mock_tech_cls.return_value.evaluate.return_value = True
        mock_bear_cls.return_value.evaluate.return_value = True

        yield {
            "client": mock_client_instance,
            "screeners": mock_screeners_instance
        }

def test_get_extra_watchlist(mock_fmp_environment):
    results = get_extra_watchlist()
    assert isinstance(results, list)
    assert "AAPL" in results

def test_run_market_down_pipeline(mock_fmp_environment):
    results = run_market_down_pipeline()
    assert isinstance(results, list)
    assert "TEST" in results

def test_run_high_growth_float_watchlist(mock_fmp_environment):
    results = run_high_growth_float_watchlist()
    assert isinstance(results, list)
    assert "TEST" in results


def test_run_swing_trading_pipeline(mock_fmp_environment):
    # Override mock screener return specifically for swing trading (Price <= yearHigh * 0.95 and relativeVolume > 1.5)
    mock_fmp_environment["client"].get_company_screener.return_value = [
        {
            "symbol": "TEST",
            "companyName": "Test Corp",
            "marketCap": 5000000000,
            "price": 85.0,           # Meets <= 100 * 0.95 (95.0)
            "yearHigh": 100.0,
            "relativeVolume": 1.8    # Meets > 1.5
        }
    ]

    results = run_swing_trading_pipeline()
    assert isinstance(results, list)
    assert "TEST" in results

def test_run_new_highs_pipeline(mock_fmp_environment):
    results = run_new_highs_pipeline()
    assert isinstance(results, list)
    assert "TEST" in results
