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


@pytest.mark.parametrize("ticker", ["AAPL", "MSFT"])
def test_full_pipeline_real_ticker(fmp_client, ticker):
    """
    Integration test validating the full end-to-end pipeline ingestion and enrichment 
    for real market tickers (AAPL, MSFT).
    """
    logger.info(f"🚀 Running full pipeline integration test on real ticker: {ticker}")

    # 1. Initialize Validators
    fund_validator = FundamentalValidator(
        client=fmp_client,
        min_eps_growth=-999.0,
        min_roe=-999.0,
        min_gross_margin=-999.0,
        max_institutional_ownership=1.0
    )
    tech_validator = TechnicalValidator(
        client=fmp_client, 
        strict_mode=False, 
        throttle_seconds=1
    )

    # 2. Mock incoming raw candidate payload
    candidate = {
        "symbol": ticker,
        "strategy_name": "real_ticker_integration_test",
        "timestamp": "2026-11-02T20:18:00Z"
    }

    # 3. Step 1: Fundamental Enrichment
    enriched_fund = fund_validator.evaluate(candidate)
    assert enriched_fund is not None, f"Fundamental validation returned None for {ticker}"

    # 4. Step 2: Technical & TA Indicator Enrichment (OBV, CMF, Choppiness, SMAs, etc.)
    enriched_tech = tech_validator.evaluate(enriched_fund)
    assert enriched_tech is not None, f"Technical validation returned None for {ticker}"

    # 5. Step 3: Quote & Profile Context Enrichment
    try:
        quote_data = fmp_client.get_quote(ticker)
        if quote_data and isinstance(quote_data, list):
            q = quote_data[0]
            enriched_tech.update({
                "current_price": q.get("price"),
                "year_high": q.get("yearHigh"),
                "year_low": q.get("yearLow"),
                "relative_volume": q.get("relVolume")
            })
    except Exception as e:
        logger.warning(f"Could not fetch quote context for {ticker}: {e}")

    # 6. Assertions: Verify mandatory technical and volume confirmation fields are populated
    mandatory_fields = [
        "symbol", "price", "sma20", "sma50", "sma200", 
        "current_obv", "current_cmf", "choppiness", "demarker"
    ]
    
    for field in mandatory_fields:
        assert field in enriched_tech, f"Missing mandatory field '{field}' for {ticker}"
        assert enriched_tech[field] is not None, f"Mandatory field '{field}' evaluated to None for {ticker}"

    logger.info(f"✨ Successfully verified all pipeline fields for {ticker}! Payload keys: {list(enriched_tech.keys())}")