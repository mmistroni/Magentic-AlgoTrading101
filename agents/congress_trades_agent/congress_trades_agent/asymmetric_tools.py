# Add to src/tools.py imports
import urllib.parse
import yfinance as yf
import json
import pandas as pd
import requests
from datetime import date

# ==============================================================================
# NEW TOOL: GOVERNMENT CONTRACT CHECKER
# ==============================================================================

def check_gov_contracts_tool(ticker: str):
    """
    Alpha Validator: Checks USASpending.gov for recent government contracts awarded to this company.
    
    Use this for sectors like Defense, Healthcare, and Tech. 
    It searches for 'New Contracts' awarded in the last 30 days.
    
    Args:
        ticker (str): The stock symbol (e.g. 'LMT', 'PFE').
        
    Returns:
        JSON string containing:
        - 'total_obligated_amount': Total value of recent contracts (USD).
        - 'contract_count': Number of individual awards.
        - 'agency_names': List of agencies paying (e.g. 'Dept of Defense').
    """
    print(f"💰 Checking Government Contracts for: {ticker}")
    try:
        # 1. Get Company Name from Ticker (USASpending needs names, not tickers)
        # We use yfinance to get the official name (e.g. "Lockheed Martin Corp")
        stock = yf.Ticker(ticker)
        raw_name = stock.info.get('longName', '')
        
        # 2. Clean Name for Search (Remove "Inc", "Corp", "PLC" to improve API hits)
        search_name = raw_name.replace(',', '').replace('.', '')
        for suffix in [' Inc', ' Corp', ' PLC', ' Ltd', ' Corporation', ' Company']:
            if search_name.endswith(suffix):
                search_name = search_name[:-len(suffix)]
        
        if not search_name:
            return json.dumps({"ticker": ticker, "error": "Could not resolve company name"})

        # 3. Query the USASpending API
        contracts = _fetch_usaspending_data(search_name)
        
        return json.dumps({
            "ticker": ticker,
            "search_name": search_name,
            "recent_contracts_found": True if contracts['total_amount'] > 0 else False,
            "total_obligated_amount": f"${contracts['total_amount']:,.2f}",
            "contract_count": contracts['count'],
            "top_agencies": contracts['agencies']
        })

    except Exception as e:
        print(f"Contract Tool Error: {e}")
        return json.dumps({"ticker": ticker, "error": "API Lookup Failed"})

# ==============================================================================
# INTERNAL HELPER (USASpending API Logic)
# ==============================================================================

def _fetch_usaspending_data(company_name: str) -> dict:
    """
    Hits the api.usaspending.gov/api/v2/search/spending_by_award/ endpoint.
    Filters for last 30 days.
    """
    url = "https://api.usaspending.gov/api/v2/search/spending_by_award/"
    
    # Calculate Date Range (Last 30 Days)
    today = date.today()
    start_date = (today - pd.Timedelta(days=30)).strftime("%Y-%m-%d")
    end_date = today.strftime("%Y-%m-%d")
    
    payload = {
        "filters": {
            # Keyword search matches company name
            "keyword": company_name, 
            # Filter by Time Period
            "time_period": [{"start_date": start_date, "end_date": end_date}],
            # Filter for CONTRACTS only (Type A, B, C, D) - ignores grants/loans
            "award_type_codes": ["A", "B", "C", "D"]
        },
        "fields": ["Award Amount", "Awarding Agency"],
        "limit": 50,
        "page": 1
    }
    
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(url, json=payload, headers=headers, timeout=10)
        data = response.json()
        
        total_money = 0.0
        agencies = set()
        count = 0
        
        for item in data.get('results', []):
            amount = item.get('Award Amount', 0)
            if amount > 0:
                total_money += amount
                agencies.add(item.get('Awarding Agency', 'Unknown'))
                count += 1
                
        return {
            "total_amount": total_money,
            "count": count,
            "agencies": list(agencies)[:3] # Top 3 agencies
        }
        
    except Exception:
        return {"total_amount": 0, "count": 0, "agencies": []}