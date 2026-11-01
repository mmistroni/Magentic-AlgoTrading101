import os
import pytest
import logging
from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

@pytest.fixture
def live_client():
    """Fixture that initializes the client with a real API key, or skips if not available."""
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        pytest.skip("FMP_API_KEY environment variable not set. Skipping live integration tests.")
    return FMPClient(api_key=api_key)

def test_live_company_screener(live_client):
    """Verifies get_company_screener returns active US equities matching criteria."""
    params = {
        "marketCapMoreThan": 50000000000,  # $50B+ companies
        "limit": 3
    }
    results = live_client.get_company_screener(params)
    
    assert isinstance(results, list), "Expected list response from company screener"
    assert len(results) > 0, "Company screener returned zero results."
    
    sample = results[0]
    print(f"\n[Screener Success] Symbol: {sample.get('symbol')} | Price: {sample.get('price')}")
    assert "symbol" in sample
    assert "price" in sample

def test_live_financial_growth(live_client):
    """Verifies get_financial_growth returns historical income statement growth items for a ticker."""
    symbol = "AAPL"
    results = live_client.get_financial_growth(symbol)
    
    assert isinstance(results, list), f"Expected list for financial growth of {symbol}"
    assert len(results) > 0, f"Financial growth returned empty for {symbol}. Check endpoint path or subscription tier."
    
    sample = results[0]
    print(f"\n[Financial Growth Success] {symbol} EPS Growth: {sample.get('epsgrowth')}")
    assert any(k in sample for k in ["epsgrowth", "revenueGrowth", "netIncomeGrowth"])

def test_live_balance_sheet_growth(live_client):
    """Verifies get_balance_sheet_growth returns balance sheet growth metrics."""
    symbol = "AAPL"
    results = live_client.get_balance_sheet_growth(symbol)
    
    assert isinstance(results, list), f"Expected list for balance sheet growth of {symbol}"
    assert len(results) > 0, f"Balance sheet growth returned empty for {symbol}."
    
    sample = results[0]
    print(f"\n[Balance Sheet Growth Success] {symbol} Asset Growth: {sample.get('growthTotalAssets')}")
    assert "growthTotalAssets" in sample or "growthTotalDebt" in sample

def test_live_cash_flow_growth(live_client):
    """Verifies get_cash_flow_growth returns cash flow statement growth metrics."""
    symbol = "AAPL"
    results = live_client.get_cash_flow_growth(symbol)
    
    assert isinstance(results, list), f"Expected list for cash flow growth of {symbol}"
    assert len(results) > 0, f"Cash flow growth returned empty for {symbol}."
    
    sample = results[0]
    print(f"\n[Cash Flow Growth Success] {symbol} Free Cash Flow Growth: {sample.get('growthFreeCashFlow')}")
    assert "growthFreeCashFlow" in sample or "growthOperatingCashFlow" in sample

def test_live_key_metrics_ttm(live_client):
    """Verifies get_key_metrics_ttm returns trailing twelve month metrics."""
    symbol = "AAPL"
    results = live_client.get_key_metrics_ttm(symbol)
    
    assert isinstance(results, list), f"Expected list for key metrics TTM of {symbol}"
    assert len(results) > 0, f"Key metrics TTM returned empty for {symbol}."
    
    sample = results[0]
    print(f"\n[Key Metrics TTM Success] {symbol} ROE TTM: {sample.get('returnOnEquityTTM')}")
    assert "returnOnEquityTTM" in sample or "grossProfitMarginTTM" in sample

def test_live_institutional_ownership_summary(live_client):
    """Verifies get_institutional_ownership_summary returns ownership metrics."""
    symbol = "AAPL"
    summary = live_client.get_institutional_ownership_summary(symbol)
    
    assert isinstance(summary, dict), "Expected dictionary summary for institutional ownership"
    print(f"\n[Institutional Ownership Success] {symbol} Summary Keys: {list(summary.keys())[:5]}")
    assert summary is not None

def test_live_sma_endpoint(live_client):
    """Verifies get_sma returns technical indicator moving averages across periods."""
    symbol = "AAPL"
    for period in [20, 50, 200]:
        data = live_client.get_sma(symbol=symbol, period_length=period, timeframe="1day")
        assert isinstance(data, list), f"Expected list for SMA {period}"
        if data:
            latest = data[0]
            print(f"\n[SMA Success] {symbol} SMA({period}): close={latest.get('close')}, sma={latest.get('sma')}")
            assert "sma" in latest

def test_live_quote_endpoint(live_client):
    """Verifies get_quote returns real-time pricing data including yearHigh and yearLow."""
    symbol = "AAPL"
    results = live_client.get_quote(symbol)
    
    assert isinstance(results, list), f"Expected list for quote of {symbol}"
    assert len(results) > 0, f"Quote returned empty for {symbol}."
    
    sample = results[0]
    print(f"\n[Quote Success] {symbol} Price: {sample.get('price')} | 52W High: {sample.get('yearHigh')} | 52W Low: {sample.get('yearLow')}")
    
    assert "price" in sample
    assert "yearHigh" in sample
    assert "yearLow" in sample