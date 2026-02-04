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
    bq_client = bigquery.Client(project="datascience-projects")
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
    
    # We return the list, but the agent will see the size in its thought process
    # --- DEBUGGING ---
    print(f"✅ [STEP 1] Found {len(results)} raw candidates at Offset: {offset}")
    return results
    return results

# --- TOOL 2: Technical Confirmation ---
import math # Add this at the top

def get_technical_metrics_tool(tickers: str, target_date: str) -> str:
    """
    Step 2: Filters a batch of tickers based on the 200-day Simple Moving Average (SMA).
    Calculates technicals as of the public disclosure date (target_date + 45 days).
    
    Args:
        tickers (str): A single space-separated string of tickers (e.g., "AAPL MSFT TSLA").
        target_date (str): The quarter-end filing date (YYYY-MM-DD).
        
    Returns:
        str: A space-separated string containing ONLY the tickers that are currently 
             trading above their 200-day SMA. Use this string for the next tool.
             Example: "AAPL NVDA MSFT"
    """
    import math
    import time
    start_time = time.time()
    
    public_date = date.fromisoformat(target_date) + timedelta(days=45)
    ticker_list = tickers.split()
    
    import time
    start_time = time.time()

    # threads=True is used here to prevent the 'huge amount of time' delay 
    # by downloading historical data in parallel.
    data = yf.download(ticker_list, 
                       start=public_date - timedelta(days=365), 
                       end=public_date, 
                       group_by='ticker',
                       progress=False, 
                       auto_adjust=True,
                       threads=True)
    end_time = time.time()
    print(f"⏱️ DEBUG: Technical check for {len(ticker_list)} stocks took {round(end_time - start_time, 2)} seconds.")
    
    results = []
    for ticker in ticker_list:
        try:
            t_data = data[ticker] if len(ticker_list) > 1 else data
            if t_data.empty or len(t_data) < 200:
                continue
                
            current_price = t_data['Close'].iloc[-1]
            sma_200 = t_data['Close'].rolling(window=200).mean().iloc[-1]
            
            # --- CRITICAL FIX: NaN Protection ---
            safe_price = float(current_price) if not math.isnan(current_price) else 0.0
            safe_sma = float(sma_200) if not math.isnan(sma_200) else 0.0
            
            # Trend Filter Logic
            if safe_price > safe_sma and safe_price > 0:
                results.append(ticker) # We only need the ticker string now
                
        except Exception as e:
            print(f"DEBUG: Error processing {ticker}: {e}")
            continue

    # --- PERFORMANCE & TOKEN DEBUGGING ---
    end_time = time.time()
    elapsed = round(end_time - start_time, 2)
    print(f"⏱️ [STEP 2] Processed {len(ticker_list)} tickers in {elapsed}s.")
    print(f"🔍 [STEP 2] {len(results)} stocks passed the 200DMA filter.")
    
    # Returning a joined string significantly reduces the context window 
    # size compared to returning a list of dictionaries.
    passing_string = " ".join(results)
    return passing_string


# --- TOOL 3: Performance Audit ---
def get_forward_return_tool(tickers: str, target_date: str, days_ahead: int = 180) -> list:
    """
    Step 3: Calculates the forward ROI for a list of tickers.
    USE THIS tool only after tickers have been confirmed by the Technical Tool.
    
    Args:
        tickers (str): A SINGLE space-separated string of tickers (e.g., "AAPL MSFT TSLA").
        target_date (str): The quarter-end date (YYYY-MM-DD).
        days_ahead (int): The investment horizon (default 180).
    Returns:
        list: A list of dicts containing ROI data, entry, and exit prices.
    """
    import math
    start_dt = date.fromisoformat(target_date) + timedelta(days=45)
    end_dt = start_dt + timedelta(days=days_ahead)
    ticker_list = tickers.split()

    # --- DEBUGGING ---
    print(f"📊 [STEP 3] Running final ROI Audit on {len(ticker_list)} tickers...")


    
    # --- CONSOLE DEBUGGING ---
    print(f"\n[AUDIT START] Target Date: {target_date} | Entry: {start_dt}")
    print(f"[AUDIT BATCH] Processing {len(ticker_list)} tickers...")
    
    # Download all tickers in one block to optimize network calls
    data = yf.download(ticker_list, start=start_dt, end=end_dt + timedelta(days=10), 
                        group_by='ticker', progress=False, auto_adjust=True, threads=True)
    
    results = []
    for ticker in ticker_list:
        try:
            # Handle single vs multiple ticker dataframe structure
            t_data = data[ticker] if len(ticker_list) > 1 else data
            
            if t_data.empty or len(t_data) < 2:
                print(f"  - {ticker}: Skipping (Insufficient Data)")
                continue
                
            entry_p = t_data['Close'].iloc[0]
            exit_p = t_data['Close'].iloc[-1]
            
            # --- NAN PROTECTION ---
            if not math.isnan(entry_p) and not math.isnan(exit_p):
                roi = round(float((exit_p - entry_p) / entry_p * 100), 2)
                results.append({
                    "ticker": ticker,
                    "return_pct": roi,
                    "entry_price": round(float(entry_p), 2),
                    "exit_price": round(float(exit_p), 2),
                    "start_date": start_dt.strftime('%Y-%m-%d'),
                    "end_date": end_dt.strftime('%Y-%m-%d')
                })
            else:
                print(f"  - {ticker}: Skipping (NaN values found)")
        except Exception as e:
            print(f"  - {ticker}: Error - {e}")
            continue
            
    print(f"[AUDIT COMPLETE] Successfully processed {len(results)}/{len(ticker_list)} tickers.\n")
    return results