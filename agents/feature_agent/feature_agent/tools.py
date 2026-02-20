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

def get_technical_metrics_tool(tickers: str, target_date: str, strict_mode: bool = True, mode: str = "backtest") -> str:
    """
    Step 2 & 5 Filter: Handles both historical audits and live March 2026 execution.
    
    Args:
        tickers (str): Space-separated tickers.
        target_date (str): Quarter-end date (e.g., '2023-12-31').
        strict_mode (bool): If True, stock must beat SPY.
        mode (str): "backtest" for historical dates or "live" for current market data.
    """
    import math
    import time
    import pandas as pd
    import yfinance as yf
    from datetime import date, datetime, timedelta

    # --- 1. DETERMINE EVALUATION DATE ---
    # If live, we use TODAY. If backtest, we use the 45-day delay logic.
    if mode == "live":
        eval_date = date.today()
    else:
        eval_date = date.fromisoformat(target_date) + timedelta(days=45)

    ticker_list = list(set(tickers.split())) 
    
    # FETCH BENCHMARK DATA (SPY)
    spy_start = eval_date - timedelta(days=95)
    spy_data = yf.download("SPY", start=spy_start, end=eval_date, progress=False, auto_adjust=True)
    
    spy_return = 0.0
    if not spy_data.empty and len(spy_data) >= 2:
        spy_return = (spy_data['Close'].iloc[-1] - spy_data['Close'].iloc[0]) / spy_data['Close'].iloc[0]

    # FETCH PORTFOLIO DATA
    history_start = eval_date - timedelta(days=365)
    data = yf.download(ticker_list, 
                       start=history_start, 
                       end=eval_date, 
                       group_by='ticker',
                       progress=False, 
                       auto_adjust=True,
                       threads=True)

    results = []
    
    for ticker in ticker_list:
        try:
            t_data = data[ticker] if len(ticker_list) > 1 else data
            t_data = t_data.dropna(subset=['Close'])

            if t_data.empty or len(t_data) < 200:
                continue
                
            current_price = float(t_data['Close'].iloc[-1])
            sma_200 = float(t_data['Close'].rolling(window=200).mean().iloc[-1])
            sma_50 = float(t_data['Close'].rolling(window=50).mean().iloc[-1])
            
            idx_3m = -63 if len(t_data) >= 63 else 0
            start_price_3m = float(t_data['Close'].iloc[idx_3m])
            stock_3m_return = (current_price - start_price_3m) / start_price_3m
            
            if any(math.isnan(x) for x in [current_price, sma_200, stock_3m_return]):
                continue
            
            # --- SELECTION & CRITIQUE LOGIC ---
            # Condition 1: Must be in a long-term uptrend (Crucial for Live Mode)
            if current_price > sma_200:
                is_passing = False
                if strict_mode:
                    if stock_3m_return > spy_return:
                        is_passing = True
                else:
                    if stock_3m_return > 0:
                        is_passing = True
                
                if is_passing:
                    # In addition to the ticker, we append technical metadata 
                    # so the Critique Agent in Step 5 knows the SMA health.
                    results.append(f"{ticker}(SMA200:UP|SMA50:{'UP' if current_price > sma_50 else 'DOWN'})")
                
        except Exception:
            continue

    mode_desc = f"{mode.upper()} - {'STRICT' if strict_mode else 'RELAXED'}"
    print(f"🔍 [STEP 2/5] Mode: {mode_desc} | Date: {eval_date} | {len(results)} passed.")
    
    return " ".join(results)


# --- TOOL 3: Performance Audit ---
# --- TOOL 3: Performance Audit (AMENDED WITH SANITIZATION) ---
def get_forward_return_tool(tickers: str, target_date: str, days_ahead: int = 180) -> list:
    """
    Step 3: Calculates the forward ROI for a list of tickers.
    Automatically handles sanitization of tickers containing SMA metadata.
    """
    import math
    import re # Ensure regex is imported
    
    # --- NEW: SANITIZATION LOGIC ---
    # This regex removes anything inside parentheses for every ticker in the string
    clean_tickers_str = re.sub(r'\(.*?\)', '', tickers)
    ticker_list = clean_tickers_str.split()
    # -------------------------------

    start_dt = date.fromisoformat(target_date) + timedelta(days=45)
    end_dt = start_dt + timedelta(days=days_ahead)

    # --- DEBUGGING ---
    print(f"📊 [STEP 3] Running final ROI Audit on {len(ticker_list)} tickers...")
    print(f"  - Cleaned Tickers: {', '.join(ticker_list)}")
    
    # Download all tickers in one block
    data = yf.download(ticker_list, start=start_dt, end=end_dt + timedelta(days=10), 
                        group_by='ticker', progress=False, auto_adjust=True, threads=True)
    
    results = []
    for ticker in ticker_list:
        try:
            t_data = data[ticker] if len(ticker_list) > 1 else data
            
            if t_data.empty or len(t_data) < 2:
                print(f"  - {ticker}: Skipping (Insufficient Data)")
                continue
                
            entry_p = t_data['Close'].iloc[0]
            exit_p = t_data['Close'].iloc[-1]
            
            if not math.isnan(entry_p) and not math.isnan(exit_p):
                roi = round(float((exit_p - entry_p) / entry_p * 100), 2)
                results.append({
                    "ticker": ticker,
                    "return_pct": roi,
                    "entry_price": round(float(entry_p), 2),
                    "exit_price": round(float(exit_p), 2)
                })
        except Exception as e:
            print(f"  - {ticker}: Error - {e}")
            continue
            
    return results

import re

def _sanitize_ticker(ticker_with_metadata: str) -> str:
    """
    Strips metadata like (SMA200:UP) from a ticker string.
    Input: "AAPL(SMA200:UP|SMA50:DOWN)"
    Output: "AAPL"
    """
    return re.sub(r'\(.*\)', '', ticker_with_metadata).strip()

# Example usage in your Step 4 loop:
# for raw_ticker in results.split():
#     clean_ticker = sanitize_ticker(raw_ticker)
#     return_data = get_forward_return_tool(clean_ticker, target_date)