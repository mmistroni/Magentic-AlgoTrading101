from datetime import date, timedelta
import os
import pandas as pd
from google.cloud import bigquery
import requests

# --- TOOL 1: BigQuery Historical Consensus ---
def fetch_consensus_holdings_tool(target_date: str) -> list:
    """
    Step 1: Finds high-conviction 'Elite' picks for a specific quarter-end date.
    Use this tool FIRST to get the list of tickers to analyze.
    
    Args:
        target_date (str): The quarter-end date (e.g., '2024-12-31'). 
                          Must be in YYYY-MM-DD format.
    Returns:
        list: A list of dictionaries containing 'ticker' and 'manager_count'.
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
    return df.to_dict(orient='records')


import yfinance as yf
from datetime import date, timedelta

# --- TOOL 2: Technical Confirmation (yf version) ---
def get_technical_metrics_tool(tickers: str, target_date: str) -> list:
    """
    Step 2: Verifies 200DMA for a LIST of tickers in one single request.
    Use this to avoid the agent getting stuck in a loop.
    
    Args:
        tickers: A space-separated string of symbols (e.g. 'PLTR MSFT AAPL')
        target_date: The quarter-end date YYYY-MM-DD.
    """
    public_date = date.fromisoformat(target_date) + timedelta(days=45)
    ticker_list = tickers.split()
    
    # yf.download handles lists of tickers in parallel automatically!
    data = yf.download(ticker_list, 
                       start=public_date - timedelta(days=365), 
                       end=public_date, 
                       group_by='ticker',
                       progress=False, 
                       auto_adjust=True)
    
    results = []
    for ticker in ticker_list:
        try:
            # Handle both single and multi-index dataframes from yfinance
            t_data = data[ticker] if len(ticker_list) > 1 else data
            if t_data.empty or len(t_data) < 200:
                results.append({"ticker": ticker, "is_above_200dma": False, "error": "No history"})
                continue
                
            current_price = t_data['Close'].iloc[-1]
            sma_200 = t_data['Close'].rolling(window=200).mean().iloc[-1]
            
            results.append({
                "ticker": ticker,
                "is_above_200dma": bool(current_price > sma_200),
                "price_at_entry": round(float(current_price), 2)
            })
        except Exception:
            results.append({"ticker": ticker, "is_above_200dma": False, "error": "Fail"})
            
    return results


# --- TOOL 3: Performance Audit (yf version) ---
def get_forward_return_tool(ticker: str, target_date: str, days_ahead: int = 180) -> dict:
    """
    Step 3: Calculates the ROI starting from the public knowledge date.
    ONLY call this tool if 'is_above_200dma' was True in Step 2.
    """
    start = date.fromisoformat(target_date) + timedelta(days=45)
    end = start + timedelta(days=days_ahead)
    
    # Download small window around entry and exit
    data = yf.download(ticker, start=start, end=end + timedelta(days=10), 
                       progress=False, auto_adjust=True)
    
    if len(data) < 2:
        return {"ticker": ticker, "error": "Insufficient data for return calculation"}
        
    entry_price = data['Close'].iloc[0]
    exit_price = data['Close'].iloc[-1]
    
    return {
        "ticker": ticker, 
        "return_pct": round(float((exit_price - entry_price) / entry_price * 100), 2)
    }


def get_latest_prices_fmp(symbol:str, start_date : date, end_date :date) -> pd.DataFrame:
    
    api_key = os.environ['FMP_KEY']
    base_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?from={start_date.strftime('%Y-%m-%d')}&to={end_date.strftime('%Y-%m-%d')}&apikey={api_key}"

    try:
        response = requests.get(base_url)
        data = response.json()

        # FIX 1: Check if 'historical' key exists and is not empty
        if 'historical' in data and data['historical']:
            # We sort by date (ascending) so iloc[0] is the entry and iloc[-1] is the exit
            res = data['historical'][::-1]
            return pd.DataFrame(data=res)
        else:
            # FIX 2: Return an empty DataFrame instead of crashing
            return pd.DataFrame()

    except Exception as e:
        print(f"Connection error for {symbol}: {e}")
        return pd.DataFrame()

