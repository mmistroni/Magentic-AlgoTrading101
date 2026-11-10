import os
import logging
import pytest
from ingest_fmp.client import FMPClient
from ingest_fmp.fundamental_validator import FundamentalValidator
from ingest_fmp.technical_validator import TechnicalValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def fmp_client():
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        pytest.skip("FMP_API_KEY environment variable not set. Skipping full pipeline integration test.")
    return FMPClient(api_key=api_key)


def test_full_pipeline_symbol_ingestion(fmp_client):
    """
    Simulates the end-to-end pipeline ingestion flow for a test symbol (AAPL)
    to verify database-ready payload completeness.
    """
    logger.info("🚀 Starting full pipeline integration test...")

    # 1. Initialize Validators with relaxed diagnostic thresholds
    fund_validator = FundamentalValidator(
        client=fmp_client,
        min_eps_growth=-999.0,
        min_roe=-999.0,
        min_gross_margin=-999.0,
        max_institutional_ownership=1.0
    )
    tech_validator = TechnicalValidator(
        client=fmp_client, 
        strict_mode=False,  # Relaxed for testing inspection
        throttle_seconds=1
    )

    # 2. Mock incoming raw candidate payload from pipeline source
    candidate = {
        "symbol": "AAPL",
        "strategy_name": "pipeline_integration_test",
        "timestamp": "2026-11-02T20:18:00Z"
    }

    # 3. Step 1: Fundamental Enrichment
    enriched_fund = fund_validator.evaluate(candidate)
    assert enriched_fund, "Pipeline failed at FundamentalValidator step."
    logger.info("✅ Fundamental validation step passed.")

    # 4. Step 2: Technical & TA Indicator Enrichment
    enriched_tech = tech_validator.evaluate(enriched_fund)
    assert enriched_tech, "Pipeline failed at TechnicalValidator step."
    logger.info("✅ Technical & TA indicator computation step passed.")

    # 5. Step 3: Quote & Profile Context Enrichment (matching pipeline DoFn)
    try:
        quote_data = fmp_client.get_quote("AAPL")
        if quote_data and isinstance(quote_data, list):
            q = quote_data[0]
            enriched_tech.update({
                "current_price": q.get("price"),
                "year_high": q.get("yearHigh"),
                "year_low": q.get("yearLow"),
                "relative_volume": q.get("relVolume")
            })
    except Exception as e:
        logger.warning(f"Could not fetch supplemental quote data: {e}")

    # 6. Final Comprehensive Assertion Check for Agent & BigQuery Schema
    required_pipeline_fields = [
        "symbol", "strategy_name", 
        "eps_growth", "revenue_growth", "return_on_equity", "gross_margin",
        "price", "sma20", "sma50", "sma200", "technical_passed",
        "current_obv", "current_cmf", "choppiness", "demarker"
    ]

    for field in required_pipeline_fields:
        assert field in enriched_tech, f"Pipeline output missing mandatory field: {field}"
        assert enriched_tech[field] is not None, f"Pipeline field {field} evaluated to None."

    logger.info(f"✨ Full pipeline integration test passed successfully! Final keys count: {len(enriched_tech)}")