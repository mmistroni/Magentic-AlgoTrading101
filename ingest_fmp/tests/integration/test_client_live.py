import os
import pytest
from ingest_fmp.client import FMPClient

@pytest.fixture
def live_client():
    """Fixture that initializes the client with a real API key, or skips if not available."""
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        pytest.skip("FMP_API_KEY environment variable not set. Skipping live integration test.")
    return FMPClient(api_key=api_key)

def test_live_company_screener(live_client):
    """
    Real integration test hitting the live FMP Company Screener endpoint 
    to verify network access, schema, and feasibility.
    """
    # Use a narrow query (e.g., large cap, small limit) to ensure a fast, lightweight response
    params = {
        "marketCapMoreThan": 50000000000,  # $50B+ companies
        "limit": 3
    }

    results = live_client.get_company_screener(params)

    # Assertions to validate live data structure
    assert isinstance(results, list), "Expected list response from live FMP API"
    assert len(results) > 0, "Live screener returned zero results — check endpoint or parameters."

    # Inspect the keys of the first returned stock to confirm fields match expectations
    sample_stock = results[0]
    print(f"\n--- Live API Success Sample ---")
    print(f"Symbol: {sample_stock.get('symbol')}")
    print(f"Company: {sample_stock.get('companyName')}")
    print(f"Price: {sample_stock.get('price')}")
    print(f"Market Cap: {sample_stock.get('marketCap')}")
    print(f"-------------------------------")

    assert "symbol" in sample_stock
    assert "price" in sample_stock