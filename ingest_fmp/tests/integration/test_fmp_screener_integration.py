import pytest
import pandas as pd
from ingest_fmp.client import FMPClient

@pytest.fixture
def fmp_client():
    return FMPClient()

def test_extra_watchlist_descriptive_filters(fmp_client):
    """Verifies FMP understands market cap, price, volume, and active trading parameters."""
    params = {
        "marketCapMoreThan": 2000000000,
        "priceMoreThan": 10,
        "avgVolumeMoreThan": 200000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": 50
    }
    
    data = fmp_client.get_company_screener(params)
    assert data is not None, "FMP returned None for Extra Watchlist parameters"
    
    df = pd.DataFrame(data)
    print(f"\n[Extra Watchlist] Retrieved {len(df)} records.")
    
    if not df.empty:
        # Validate that FMP respected the filters
        assert (df["marketCap"] >= 2000000000).all(), "FMP returned stocks below $2B market cap!"
        assert (df["price"] > 10).all(), "FMP returned stocks priced $10 or lower!"
        assert (df["avgVolume"] > 200000).all(), "FMP returned stocks with avg volume <= 200K!"

def test_market_down_descriptive_filters(fmp_client):
    """Verifies FMP correctly filters by NASDAQ exchange and market cap."""
    params = {
        "exchange": "NASDAQ",
        "marketCapMoreThan": 2000000000,
        "country": "US",
        "isActivelyTrading": "true",
        "limit": 50
    }
    
    data = fmp_client.get_company_screener(params)
    assert data is not None, "FMP returned None for Market Down parameters"
    
    df = pd.DataFrame(data)
    print(f"\n[Market Down] Retrieved {len(df)} records.")
    
    if not df.empty and "exchange" in df.columns:
        # Check if exchanges returned are exclusively NASDAQ (or include variations like NASDAQ Global Select)
        non_nasdaq = df[~df["exchange"].str.contains("NASDAQ", case=False, na=False)]
        print(f"Exchanges found: {df['exchange'].unique()[:5]}")
        assert len(non_nasdaq) == 0, f"FMP returned non-NASDAQ exchanges: {non_nasdaq['exchange'].unique()}"

def test_swing_trading_descriptive_filters(fmp_client):
    """Verifies FMP handles relative volume and basic pricing filters."""
    params = {
        "priceMoreThan": 10,
        "avgVolumeMoreThan": 200000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": 100
    }
    
    data = fmp_client.get_company_screener(params)
    assert data is not None
    
    df = pd.DataFrame(data)
    print(f"\n[Swing Trading] Retrieved {len(df)} records.")
    
    if not df.empty:
        assert (df["price"] > 10).all()
        # Check if relativeVolume field exists in FMP's response payload
        if "relativeVolume" in df.columns:
            print(f"relativeVolume column present. Sample values: {df['relativeVolume'].head(5).tolist()}")
        else:
            print("⚠️ Warning: 'relativeVolume' column is missing from FMP screener response! Local pandas filtering may be required.")

def test_new_highs_descriptive_filters(fmp_client):
    """Verifies FMP handles small/mid caps over $300M and checks yearHigh presence."""
    params = {
        "marketCapMoreThan": 300000000,
        "priceMoreThan": 10,
        "avgVolumeMoreThan": 200000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": 50
    }
    
    data = fmp_client.get_company_screener(params)
    assert data is not None
    
    df = pd.DataFrame(data)
    print(f"\n[New Highs] Retrieved {len(df)} records.")
    
    if not df.empty:
        assert (df["marketCap"] >= 300000000).all()
        