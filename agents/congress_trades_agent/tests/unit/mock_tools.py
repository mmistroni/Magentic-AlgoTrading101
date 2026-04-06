import json

def fetch_political_signals_tool(analysis_date: str) -> str:
    """
    MOCK TOOL for the Researcher. 
    Simulates querying the 'concrete_signals_2024' or 'signals_2025_poc' view.
    """
    print(f"🔍 [MOCK] Fetching political signals for {analysis_date}...")
    
    mock_signals = [
        {
            "ticker": "BE",
            "signal_type": "GOLDEN_BUY_CONFLUENCE",
            "days_gap": -15, # Senator bought 15 days before lobbying report
            "lobbying_spend": 150000,
            "senator": "Sen. Carper",
            "net_buy_activity": 45,
            "buying_days_count": 4,
            "market_uptrend": True
        },
        {
            "ticker": "MOH",
            "signal_type": "CONGRESS_BUY", # No lobbying overlap
            "days_gap": None,
            "lobbying_spend": 0,
            "senator": "Sen. Moran",
            "net_buy_activity": 25,
            "buying_days_count": 2,
            "market_uptrend": True
        },
        {
            "ticker": "EQIX",
            "signal_type": "GOLDEN_BUY_CONFLUENCE",
            "days_gap": 5,
            "lobbying_spend": 50000,
            "senator": "Sen. Peters",
            "net_buy_activity": 35,
            "buying_days_count": 3,
            "market_uptrend": True
        }
    ]
    return json.dumps(mock_signals)


def fetch_form4_signals_tool(ticker: str) -> str:
    """
    MOCK TOOL for the Insider Analyst.
    Simulates checking SEC Form 4 database.
    """
    print(f"👔 [MOCK] Checking Form 4 Insiders for {ticker}...")
    
    insider_db = {
        "BE": {"insider_action": "Massive Accumulation", "role": "CEO", "shares_bought": 50000, "shares_sold": 0},
        "MOH": {"insider_action": "Heavy Selling", "role": "CFO", "shares_bought": 0, "shares_sold": 15000}, # Red flag!
        "EQIX": {"insider_action": "Neutral", "role": "Director", "shares_bought": 100, "shares_sold": 0}
    }
    
    return json.dumps(insider_db.get(ticker.upper(), {"error": "No insider data"}))


def check_fundamentals_tool(ticker: str) -> str:
    """
    MOCK TOOL for the Trader.
    Simulates fetching Yahoo Finance fundamentals.
    """
    print(f"📈 [MOCK] Fetching Fundamentals & Technicals for {ticker}...")
    
    financials_db = {
        "BE": {
            "sector": "Industrials", 
            "market_cap_B": 4.5, 
            "forward_pe": 25.0, 
            "debt_to_equity": 80.0, 
            "price_vs_200ma": "UPTREND", # Technicals look good
            "beta": 1.5
        },
        "MOH": {
            "sector": "Healthcare", 
            "market_cap_B": 15.0, 
            "forward_pe": 15.0, 
            "debt_to_equity": 50.0, 
            "price_vs_200ma": "DOWNTREND (FALLING KNIFE)", # Technical Red Flag!
            "beta": 0.8
        },
        "EQIX": {
            "sector": "Real Estate", 
            "market_cap_B": 75.0, 
            "forward_pe": 85.0, # Fails P/E > 50 rule
            "debt_to_equity": 250.0, # Fails Debt > 200 rule
            "price_vs_200ma": "UPTREND",
            "beta": 1.1
        }
    }
    
    return json.dumps(financials_db.get(ticker.upper(), {"error": "INVALID_ASSET"}))