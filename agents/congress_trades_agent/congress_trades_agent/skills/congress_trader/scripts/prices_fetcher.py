import os
import requests
from typing import Optional, List, Dict, Any
#

def calculate_trailing_return(
    ticker: str, 
    entry_date: str, 
    entry_price: Optional[float] = None
) -> Dict[str, Any]:
    """
    Fetches FMP historical end-of-day price data from a past entry date to current day
    and calculates the trailing return percentage to evaluate past episodic performance.
    
    Args:
        ticker: Stock symbol (e.g., 'NVDA').
        entry_date: The past timestamp or date from an episodic record ('YYYY-MM-DD').
        entry_price: Optional known entry price from the historical record.
    """
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return {"error": "FMP_API_KEY environment variable is missing."}
        
    url = f"https://financialmodelingprep.com/stable/historical-price-eod/light?symbol={ticker.upper()}&from={entry_date}&apikey={api_key}"
    
    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            return {"error": f"FMP API returned status code {response.status_code}"}
            
        data = response.json()
        if not isinstance(data, list) or len(data) < 2:
            return {"error": f"Insufficient price history found for {ticker} from {entry_date}"}
            
        # FMP light EOD array handling (oldest vs newest)
        oldest_bar = data[-1]
        newest_bar = data[0]
        
        start_price = entry_price if entry_price else oldest_bar.get("price", oldest_bar.get("close", 0.0))
        current_price = newest_bar.get("price", newest_bar.get("close", 0.0))
        
        if start_price <= 0:
            return {"error": "Invalid start price for calculation."}
            
        return_pct = ((current_price - start_price) / start_price) * 100.0
        
        return {
            "ticker": ticker.upper(),
            "entry_date": entry_date,
            "entry_price": round(start_price, 2),
            "current_price": round(current_price, 2),
            "trailing_return_pct": round(return_pct, 2)
        }
    except Exception as e:
        return {"error": f"Error calculating trailing return for {ticker}: {str(e)}"}