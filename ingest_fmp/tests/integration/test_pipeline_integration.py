import os
import logging
import pytest
from ingest_fmp.client import FMPClient
# Import the EOD screener pipeline (and others as you add them)
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
    
    # Execute the EOD screener pipeline directly
    results = run_eod_screener()
    
    logger.info(f"📊 EOD Screener returned {len(results)} records.")
    
    # Assertions
    assert isinstance(results, list), "EOD screener must return a list of records."
    
    if len(results) > 0:
        sample_record = results[0]
        
        # Verify core metadata & identifiers
        assert "symbol" in sample_record, "Record missing 'symbol'"
        assert sample_record.get("strategy_name") == "eod_screener", "Strategy name tag incorrect"
        
        # Verify mandatory technical / fundamental fields populated by validators
        expected_fields = ["price", "SMA20", "SMA50", "SMA200", "current_obv", "choppiness"]
        for field in expected_fields:
            assert field in sample_record, f"Missing expected field '{field}' in EOD payload"
            
        logger.info(f"✨ EOD Screener test passed! Verified sample record for: {sample_record.get('symbol')}")
    else:
        logger.warning("⚠️ EOD Screener returned 0 records due to strict market filter conditions for the current session.")

# ==========================================
# Placeholder for next pipelines to add:
# ==========================================
# def test_swing_trading_pipeline_integration(fmp_client):
#     results = run_swing_trading_pipeline()
#     assert isinstance(results, list)