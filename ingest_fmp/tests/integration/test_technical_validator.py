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
    Integration test for TechnicalValidator using AAPL with comprehensive 
    indicator checks (Trend + Volume/Momentum TA indicators).
    """
    # Using strict_mode=False for testing so we can inspect enriched payloads 
    # even if AAPL is experiencing a short-term pullback below SMA20.
    validator = TechnicalValidator(client=fmp_client, throttle_seconds=1, strict_mode=False)
    
    test_input = {"symbol": "AAPL", "strategy_name": "test_bullish"}
    result = validator.evaluate(test_input)
    
    logger.info(f"TechnicalValidator result for AAPL: {result}")
    
    # Verify return type is always a dictionary
    assert isinstance(result, dict)
    assert len(result) > 0, "Validator returned an empty dictionary."
    
    # 1. Verify Trend & Price Keys
    expected_trend_keys = ['price', 'sma20', 'sma50', 'sma200', 'technical_passed']
    for key in expected_trend_keys:
        assert key in result, f"Missing trend key: {key}"

    # 2. Verify Volume, Volatility & Momentum TA Indicator Keys required by Strategic Stock Analyst
    required_ta_keys = [
        'current_obv', 
        'previous_obv', 
        'obv_historical', 
        'current_cmf', 
        'previous_cmf', 
        'cmf_historical', 
        'choppiness', 
        'demarker', 
        'ewo'
    ]
    
    for key in required_ta_keys:
        assert key in result, f"Missing required TA indicator key: {key}"
        assert result[key] is not None, f"TA indicator {key} evaluated to None"

    # Verify historical list sizing
    assert isinstance(result['obv_historical'], list)
    assert len(result['obv_historical']) > 0


def test_bearish_technical_validator_live(fmp_client):
    """
    Integration test for BearishTechnicalValidator ensuring TA indicators are included.
    """
    validator = BearishTechnicalValidator(client=fmp_client, throttle_seconds=1)
    
    test_input = {"symbol": "TSLA", "strategy_name": "test_bearish"}
    result = validator.evaluate(test_input)
    
    logger.info(f"BearishTechnicalValidator result for TSLA: {result}")
    
    assert isinstance(result, dict)
    if result:
        assert "price" in result
        assert "sma20" in result
        assert "current_obv" in result
        assert "choppiness" in result


def test_base_validator_robust_symbol_extraction():
    """Unit test to ensure symbol extraction handles dict keys correctly."""
    class DummyClient:
        pass
        
    from ingest_fmp.technical_validator import BaseTechnicalValidator
    base_val = BaseTechnicalValidator(client=DummyClient())
    
    assert base_val._get_symbol({"symbol": "MSFT"}) == "MSFT"
    assert base_val._get_symbol({"ticker": "GOOGL"}) == "GOOGL"
    assert base_val._get_symbol({}) == ""