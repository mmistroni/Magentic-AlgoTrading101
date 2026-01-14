from datetime import date, timedelta
import os
import pandas as pd
from google.cloud import bigquery
import requests
import yfinance as yf

# --- TOOL 1: BigQuery Historical Consensus ---
def fetch_consensus_holdings_tool(target_date: str) -> list:
    """
    Step 1: Retrieve the high-conviction tickers from the Elite 331 managers.
    Use this tool FIRST. 
    
    Args:
        target_date (str): The quarter-end date (YYYY-MM-DD).
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
            SELECT manager_name, cusip, 
            ROW_NUMBER() OVER(PARTITION BY manager_name, filing_date ORDER BY value_usd DESC) as position_rank
            FROM `datascience-projects.gcp_shareloader.all_holdings_master`
            WHERE manager_name IN (
                SELECT manager_name FROM `datascience-projects.gcp_shareloader.high_conviction_master`
                WHERE manager_tier = 'TIER_1_ELITE'
            )
            AND filing_date = '{target_date}'
        ) base
        JOIN `datascience-projects.gcp_shareloader.map_cusip_ticker` map ON base.cusip = map.cusip
        WHERE base.position_rank <= 10
        GROUP BY 1 HAVING manager_count >= 3
        ORDER BY manager_count DESC
    """
    df = bq_client.query(query).to_dataframe()
    results = df.to_dict(orient='records')
    
    print(f"--- DEBUG: FOUND {len(results)} TICKERS ---")
    
    # We return the list, but the agent will see the size in its thought process
    return results


# --- TOOL 2: Technical Confirmation ---
def get_technical_metrics_tool(tickers: str, target_date: str) -> list:
    """
    Step 2: BULK Trend Filter. Verifies 200DMA for MANY tickers at once.
    
    CRITICAL: You MUST pass ALL tickers as a SINGLE string separated by spaces.
    Example input: "PLTR AAPL MSFT NVDA"
    
    DO NOT call this tool for one ticker at a time. This is a BULK tool only.
    
    Args:
        tickers (str): A space-separated string of ALL symbols found in Step 1.
        target_date (str): The original quarter-end date (YYYY-MM-DD).
    """
    public_date = date.fromisoformat(target_date) + timedelta(days=45)
    ticker_list = tickers.split()
    
    print(f"--- DEBUG: PROCESSING BULK REQUEST FOR {len(ticker_list)} TICKERS ---")
    
    data = yf.download(ticker_list, 
                       start=public_date - timedelta(days=365), 
                       end=public_date, 
                       group_by='ticker',
                       progress=False, 
                       auto_adjust=True)
    
    results = []
    for ticker in ticker_list:
        try:
            # Handle yf dataframe indexing for single vs multiple tickers
            t_data = data[ticker] if len(ticker_list) > 1 else data
            
            if t_data.empty or len(t_data) < 200:
                results.append({"ticker": ticker, "is_above_200dma": False, "error": "No history"})
                continue
                
            current_price = t_data['Close'].iloc[-1]
            sma_200 = t_data['Close'].rolling(window=200).mean().iloc[-1]
            
            results.append({
                "ticker": ticker,
                "is_above_200dma": bool(current_price > sma_200),
                "price_at_entry": round(float(current_price), 2),
                "sma_200": round(float(sma_200), 2)
            })
        except Exception as e:
            results.append({"ticker": ticker, "is_above_200dma": False, "error": str(e)})
            
    return results

# --- TOOL 3: Performance Audit ---
def get_forward_return_tool(ticker: str, target_date: str, days_ahead: int = 180) -> dict:
    """
    Step 3: ROI Audit. Call this INDIVIDUALLY for tickers that passed Step 2.
    
    Args:
        ticker (str): The single symbol to check.
        target_date (str): The original quarter-end date (YYYY-MM-DD).
        days_ahead (int): Holding period (default 180).
    """
    start = date.fromisoformat(target_date) + timedelta(days=45)
    end = start + timedelta(days=days_ahead)
    
    data = yf.download(ticker, start=start, end=end + timedelta(days=10), 
                       progress=False, auto_adjust=True)
    
    if len(data) < 2:
        return {"ticker": ticker, "error": "Insufficient data"}
        
    entry_price = data['Close'].iloc[0]
    exit_price = data['Close'].iloc[-1]
    
    return {
        "ticker": ticker, 
        "return_pct": round(float((exit_price - entry_price) / entry_price * 100), 2),
        "entry_price": round(float(entry_price), 2),
        "exit_price": round(float(exit_price), 2)
    }