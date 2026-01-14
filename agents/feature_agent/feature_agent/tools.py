from datetime import date, timedelta
import os
import pandas as pd
from google.cloud import bigquery
import requests
import yfinance as yf

# --- TOOL 1: BigQuery Historical Consensus ---
# --- TOOL 1: BigQuery Historical Consensus ---
def fetch_consensus_holdings_tool(target_date: str, offset: int = 0) -> list:
    """
    Step 1: Retrieve the high-conviction tickers from the Elite 331 managers.
    Use this tool FIRST. 
    
    Args:
        target_date (str): The quarter-end date (YYYY-MM-DD).
        offset (int): The starting point for the results (default 0). Use increments of 100 to paginate.
    Returns:
        list: A list of dicts. IMPORTANT: Extract all 'ticker' values from this list 
              to pass to the next tool as a SINGLE space-separated string.
    """
    bq_client = bigquery.Client()
    query = f"""
        SELECT 
    map.ticker,
    COUNT(DISTINCT base.manager_name) as manager_count
FROM (
    SELECT 
        manager_name, 
        cusip, 
        issuer_name, -- Pulled from all_holdings_master
        ROW_NUMBER() OVER(PARTITION BY manager_name ORDER BY value_usd DESC) as position_rank
    FROM `datascience-projects.gcp_shareloader.all_holdings_master`
    WHERE manager_name IN (
        SELECT manager_name 
        FROM `datascience-projects.gcp_shareloader.high_conviction_master`
        WHERE manager_tier = 'TIER_1_ELITE'
    )
    AND filing_date = '{target_date}'
    -- AMENDMENT: Filter out ETFs using issuer_name from the base table
    AND UPPER(issuer_name) NOT LIKE '%ETF%'
    AND UPPER(issuer_name) NOT LIKE '%ISHARES%'
    AND UPPER(issuer_name) NOT LIKE '%VANGUARD%'
    AND UPPER(issuer_name) NOT LIKE '%INDEX%'
    AND UPPER(issuer_name) NOT LIKE '%TRUST%'
) base
JOIN `datascience-projects.gcp_shareloader.map_cusip_ticker` map ON base.cusip = map.cusip
WHERE base.position_rank <= 10
  -- AMENDMENT: Manual Blacklist for trackers that don't have "ETF" in their name
  AND map.ticker NOT IN (
      'SPY', 'IVV', 'VOO', 'QQQ', 'VTI', 'IWM', 'AGG', 'VEA', 'IEFA', 'VWO', 
      'GLD', 'SLV', 'SCHD', 'IAU', 'BIL', 'JPST', 'SHV', 'SHY', 'TLT', 'IEF',
      'XLF', 'SCHF', 'EFA'
  )
GROUP BY 1 
HAVING manager_count >= 3
ORDER BY manager_count DESC
-- AMENDMENT: Set to 100 for pagination and use offset to sweep the full list
LIMIT 100 OFFSET {offset}
    """
    df = bq_client.query(query).to_dataframe()
    results = df.to_dict(orient='records')
    
    print(f"--- DEBUG: FOUND {len(results)} TICKERS AT OFFSET {offset} ---")
    
    # We return the list, but the agent will see the size in its thought process
    return results

# --- TOOL 2: Technical Confirmation ---
import math # Add this at the top

def get_technical_metrics_tool(tickers: str, target_date: str) -> list:
    """
    Step 2: Processes bulk tickers. 
    CLEANSE: Replaces NaN with None to prevent JSON 400 errors.
    """
    public_date = date.fromisoformat(target_date) + timedelta(days=45)
    ticker_list = tickers.split()
    
    data = yf.download(ticker_list, 
                       start=public_date - timedelta(days=365), 
                       end=public_date, 
                       group_by='ticker',
                       progress=False, 
                       auto_adjust=True)
    
    results = []
    for ticker in ticker_list:
        try:
            t_data = data[ticker] if len(ticker_list) > 1 else data
            if t_data.empty or len(t_data) < 200:
                continue
                
            current_price = t_data['Close'].iloc[-1]
            sma_200 = t_data['Close'].rolling(window=200).mean().iloc[-1]
            
            # --- CRITICAL FIX START ---
            # If values are NaN, replace them with 0.0 or None
            safe_price = float(current_price) if not math.isnan(current_price) else 0.0
            safe_sma = float(sma_200) if not math.isnan(sma_200) else 0.0
            # --- CRITICAL FIX END ---
            
            if safe_price > safe_sma and safe_price > 0:
                results.append({
                    "ticker": ticker,
                    "is_above_200dma": True,
                    "price_at_entry": round(safe_price, 2),
                    "sma_200": round(safe_sma, 2)
                })
        except Exception:
            continue
            
    return results[:25]


# --- TOOL 3: Performance Audit ---
def get_forward_return_tool(ticker: str, target_date: str, days_ahead: int = 180) -> dict:
    """
    Step 3: Calculates ROI and returns the EXACT date window used.
    """
    start_dt = date.fromisoformat(target_date) + timedelta(days=45)
    end_dt = start_dt + timedelta(days=days_ahead)
    
    # Debugging print for your console
    print(f"DEBUG: Ticker {ticker} | Entry: {start_dt} | Exit: {end_dt}")
    
    data = yf.download(ticker, start=start_dt, end=end_dt + timedelta(days=10), 
                       progress=False, auto_adjust=True)
    
    if len(data) < 2:
        return {"ticker": ticker, "error": "Insufficient data"}
        
    entry_price = data['Close'].iloc[0]
    exit_price = data['Close'].iloc[-1]
    
    return {
        "ticker": ticker, 
        "start_date": start_dt.strftime('%Y-%m-%d'), # <--- ADDED
        "end_date": end_dt.strftime('%Y-%m-%d'),     # <--- ADDED
        "return_pct": round(float((exit_price - entry_price) / entry_price * 100), 2),
        "entry_price": round(float(entry_price), 2),
        "exit_price": round(float(exit_price), 2)
    }