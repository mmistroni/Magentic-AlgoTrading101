import os
import logging
import pytest
from ingest_fmp.client import FMPClient
from ingest_fmp.technical_validator import TechnicalValidator, BearishTechnicalValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

@pytest.fixture
def fmp_client():
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        pytest.skip("FMP_API_KEY environment variable not set. Skipping live integration test.")
    return FMPClient(api_key=api_key)


def test_technical_validator_live(fmp_client):
    """
    Integration test for TechnicalValidator using AAPL.
    Note: Depending on current market conditions, AAPL may or may not pass full bullish alignment 
    (Price > SMA20 > SMA50 > SMA200), so we verify that the method executes safely 
    and returns either a populated dictionary or an empty dictionary without throwing exceptions.
    """
    validator = TechnicalValidator(client=fmp_client, throttle_seconds=1)
    
    test_input = {"symbol": "AAPL", "strategy_name": "test_bullish"}
    result = validator.evaluate(test_input)
    
    logger.info(f"TechnicalValidator result for AAPL: {result}")
    
    # Verify return type is always a dictionary
    assert isinstance(result, dict)
    
    # If AAPL passed bullish alignment, verify enriched keys are present
    if result:
        assert "price" in result
        assert "sma20" in result
        assert "sma50" in result
        assert "sma200" in result
        assert result["price"] > result["sma20"]


def test_bearish_technical_validator_live(fmp_client):
    """
    Integration test for BearishTechnicalValidator.
    """
    validator = BearishTechnicalValidator(client=fmp_client, throttle_seconds=1)
    
    # Testing with a symbol or checking execution safety
    test_input = {"symbol": "TSLA", "strategy_name": "test_bearish"}
    result = validator.evaluate(test_input)
    
    logger.info(f"BearishTechnicalValidator result for TSLA: {result}")
    
    assert isinstance(result, dict)
    if result:
        assert "price" in result
        assert "sma20" in result
        assert result["price"] < result["sma20"]


def test_base_validator_robust_symbol_extraction():
    """Unit test to ensure symbol extraction handles dict keys correctly."""
    from ingest_fmp.client import FMPClient
    # Instantiate with dummy client for unit testing helper methods
    class DummyClient:
        pass
        
    from ingest_fmp.technical_validator import BaseTechnicalValidator
    base_val = BaseTechnicalValidator(client=DummyClient())
    
    assert base_val._get_symbol({"symbol": "MSFT"}) == "MSFT"
    assert base_val._get_symbol({"ticker": "GOOGL"}) == "GOOGL"
    assert base_val._get_symbol({}) == ""