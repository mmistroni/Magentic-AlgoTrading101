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
LEFT JOIN `datascience-projects.gcp_shareloader.map_cusip_ticker` map ON base.cusip = map.cusip
WHERE base.position_rank <= 10
  AND map.ticker IS NOT NULL  -- Ensures the agent only gets actionable tickers
  -- ADD THIS: Filter out Bond/Income/ETF keywords from the issuer name
  AND NOT REGEXP_CONTAINS(UPPER(issuer_name), r'BOND|INCOME|TREASURY|GOVT|ETF|TRUST|INDEX|SHORT-TERM')
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
    Step 2: Filters tickers based on the 200-day SMA AND 3-month Relative Strength vs SPY.
    Calculates technicals as of the public disclosure date (target_date + 45 days).
    """
    import math
    import time
    import pandas as pd
    import yfinance as yf
    from datetime import date, timedelta

    start_time = time.time()
    public_date = date.fromisoformat(target_date) + timedelta(days=45)
    ticker_list = list(set(tickers.split())) # Ensure unique tickers
    
    # 1. FETCH BENCHMARK DATA (SPY) FOR RELATIVE STRENGTH
    # We look back 95 days to ensure we have a clean 90-day (3-month) window
    spy_start = public_date - timedelta(days=95)
    spy_data = yf.download("SPY", start=spy_start, end=public_date, progress=False, auto_adjust=True)
    
    if spy_data.empty or len(spy_data) < 2:
        print("❌ [STEP 2] Error: Could not fetch SPY benchmark. Falling back to SMA only.")
        spy_return = -999.0 
    else:
        spy_return = (spy_data['Close'].iloc[-1] - spy_data['Close'].iloc[0]) / spy_data['Close'].iloc[0]
        print(f"📊 [STEP 2] Benchmark (SPY) 3-month return: {round(spy_return * 100, 2)}%")

    # 2. FETCH PORTFOLIO DATA (Batch Download)
    # We need 365 days of history to calculate a 200-day SMA reliably
    history_start = public_date - timedelta(days=365)
    data = yf.download(ticker_list, 
                       start=history_start, 
                       end=public_date, 
                       group_by='ticker',
                       progress=False, 
                       auto_adjust=True,
                       threads=True)

    results = []
    
    # 3. INDIVIDUAL TICKER EVALUATION
    for ticker in ticker_list:
        try:
            # Handle single vs multiple ticker dataframe structure
            t_data = data[ticker] if len(ticker_list) > 1 else data
            
            # CRITICAL: Drop rows with NaN in 'Close' to avoid calculation errors
            t_data = t_data.dropna(subset=['Close'])

            # SURVIVORSHIP CHECK: Ensure enough data for 200-day SMA
            if t_data.empty or len(t_data) < 200:
                continue
                
            # Current Metrics
            current_price = float(t_data['Close'].iloc[-1])
            sma_200 = float(t_data['Close'].rolling(window=200).mean().iloc[-1])
            
            # RS Calculation: Compare current price to price ~63 trading days (3 months) ago
            # If the stock doesn't have 63 days of history, we use the earliest available
            idx_3m = -63 if len(t_data) >= 63 else 0
            start_price_3m = float(t_data['Close'].iloc[idx_3m])
            stock_3m_return = (current_price - start_price_3m) / start_price_3m
            
            # NAN PROTECTION
            if any(math.isnan(x) for x in [current_price, sma_200, stock_3m_return]):
                continue
            
            # --- THE SNIPER LOGIC ---
            # Condition 1: Long-term uptrend (Above 200-day SMA)
            # Condition 2: Relative Strength (Outperforming the Market)
            if current_price > sma_200 and stock_3m_return > spy_return:
                results.append(ticker)
                
        except Exception as e:
            print(f"⚠️ [STEP 2] Error processing {ticker}: {e}")
            continue

    # 4. FINAL LOGGING & RETURN
    elapsed = round(time.time() - start_time, 2)
    print(f"⏱️ [STEP 2] Processed {len(ticker_list)} tickers in {elapsed}s.")
    print(f"🔍 [STEP 2] {len(results)} stocks passed the 'Sniper' filter.")
    
    return " ".join(results)




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