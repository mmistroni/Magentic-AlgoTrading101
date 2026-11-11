import os
import logging
import pytest
from ingest_fmp.client import FMPClient
# Import all six pipeline functions
from ingest_fmp.pipeline import (
    get_extra_watchlist,
    run_market_down_pipeline,
    run_high_growth_float_watchlist,
    run_swing_trading_pipeline,
    run_new_highs_pipeline,
    run_eod_screener
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def fmp_client():
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        pytest.skip("FMP_API_KEY environment variable not set. Skipping pipeline integration test.")
    return FMPClient(api_key=api_key)


def test_eod_screener_pipeline_integration(fmp_client):
    """
    Integration test validating that run_eod_screener() successfully connects to FMP,
    applies descriptive, fundamental, and technical filters, and returns fully enriched payloads.
    """
    logger.info("🚀 Running EOD Screener pipeline integration test...")
    
    results = run_eod_screener(limit=100)  # Limit to 100 for testing purposes
    logger.info(f"📊 EOD Screener returned {len(results)} records.")
    
    assert isinstance(results, list), "EOD screener must return a list of records."
    
    if len(results) > 0:
        sample_record = results[0]
        assert "symbol" in sample_record, "Record missing 'symbol'"
        assert sample_record.get("strategy_name") == "eod_screener", "Strategy name tag incorrect"
        
        expected_fields = ["price", "SMA20", "SMA50", "SMA200", "current_obv", "choppiness"]
        for field in expected_fields:
            assert field in sample_record, f"Missing expected field '{field}' in EOD payload"
            
        logger.info(f"✨ EOD Screener test passed! Verified sample record for: {sample_record.get('symbol')}")
    else:
        logger.warning("⚠️ EOD Screener returned 0 records due to strict market filter conditions for the current session.")


def test_extra_watchlist_pipeline_integration(fmp_client):
    """
    Integration test validating the Extra Watchlist pipeline execution and enriched record outputs.
    """
    logger.info("🚀 Running Extra Watchlist pipeline integration test...")
    
    results = get_extra_watchlist(limit=100)
    logger.info(f"📊 Extra Watchlist returned {len(results)} records.")
    
    assert isinstance(results, list), "Extra Watchlist must return a list of records."
    
    if len(results) > 0:
        sample_record = results[0]
        assert "symbol" in sample_record, "Record missing 'symbol'"
        assert sample_record.get("strategy_name") == "extra_watchlist", "Strategy name tag incorrect"
        logger.info(f"✨ Extra Watchlist test passed! Verified sample record for: {sample_record.get('symbol')}")
    else:
        logger.warning("⚠️ Extra Watchlist returned 0 records for the current session filters.")


def test_market_down_pipeline_integration(fmp_client):
    """
    Integration test validating the Market Down pipeline execution and ticker list output.
    """
    logger.info("🚀 Running Market Down pipeline integration test...")
    
    results = run_market_down_pipeline(limit=100)
    logger.info(f"📊 Market Down pipeline returned {len(results)} symbols.")
    
    assert isinstance(results, list), "Market Down pipeline must return a list of symbols."
    if len(results) > 0:
        assert isinstance(results[0], str), "Market Down symbols should be string tickers."
    logger.info("✨ Market Down pipeline test completed successfully.")


def test_high_growth_float_watchlist_integration(fmp_client):
    """
    Integration test validating the High-Growth / Low-Float Watchlist pipeline.
    """
    logger.info("🚀 Running High-Growth Float pipeline integration test...")
    
    results = run_high_growth_float_watchlist(limit=100)
    logger.info(f"📊 High-Growth Float pipeline returned {len(results)} symbols.")
    
    assert isinstance(results, list), "High-Growth Float pipeline must return a list."
    logger.info("✨ High-Growth Float pipeline test completed successfully.")


def test_swing_trading_pipeline_integration(fmp_client):
    """
    Integration test validating the EOD Swing Trading Pipeline.
    """
    logger.info("🚀 Running Swing Trading pipeline integration test...")
    
    results = run_swing_trading_pipeline(limit=100)
    logger.info(f"📊 Swing Trading pipeline returned {len(results)} symbols.")
    
    assert isinstance(results, list), "Swing Trading pipeline must return a list."
    logger.info("✨ Swing Trading pipeline test completed successfully.")


def test_new_highs_pipeline_integration(fmp_client):
    """
    Integration test validating the New Highs Momentum Pipeline.
    """
    logger.info("🚀 Running New Highs pipeline integration test...")
    
    results = run_new_highs_pipeline(limit=100)  # Limit to 50 for testing purposes
    logger.info(f"📊 New Highs pipeline returned {len(results)} symbols.")
    
    assert isinstance(results, list), "New Highs pipeline must return a list."
    logger.info("✨ New Highs pipeline test completed successfully.")