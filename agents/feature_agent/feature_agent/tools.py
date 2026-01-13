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

# --- TOOL 2: Technical Confirmation ---
def get_technical_metrics_tool(ticker: str, target_date: str) -> dict:
    """
    Step 2: Verifies if a stock was above its 200-day Moving Average (DMA).
    Call this tool for every ticker returned by Step 1.
    
    CRITICAL: This tool automatically accounts for the 45-day SEC filing lag.
    Pass the SAME target_date used in Step 1.
    
    Args:
        ticker (str): The stock symbol (e.g., 'PLTR').
        target_date (str): The quarter-end date in YYYY-MM-DD format.
    """
    # Publicly available date is 45 days after quarter end
    public_date = date.fromisoformat(target_date) + timedelta(days=45)
    
    # Download extra data to calculate the 200DMA accurately
    data = get_latest_prices_fmp(ticker, start_date = public_date - timedelta(days=300), 
                                 end_date = public_date)
    
    if data.empty:
        return {"ticker": ticker, "error": "No price data found"}

    current_price = data['close'].iloc[-1]
    sma_200 = data['close'].rolling(window=200).mean().iloc[-1]
    
    return {
        "ticker": ticker,
        "is_above_200dma": bool(current_price > sma_200),
        "price_at_entry": round(float(current_price), 2),
        "sma_200": round(float(sma_200), 2)
    }

# --- TOOL 3: Performance Audit ---
def get_forward_return_tool(ticker: str, target_date: str, days_ahead: int = 180) -> dict:
    """
    Step 3: Calculates the 6-month ROI starting from the public knowledge date.
    ONLY call this tool if 'is_above_200dma' was True in Step 2.
    
    Args:
        ticker (str): The stock symbol.
        target_date (str): The quarter-end date (the tool adds the 45-day lag).
        days_ahead (int): Holding period in days. Defaults to 180 (6 months).
    """
    start = date.fromisoformat(target_date) + timedelta(days=45)
    end = start + timedelta(days=days_ahead)
    
    data = get_latest_prices_fmp(ticker, start_date=start, end_date=end + timedelta(days=7))
    
    if len(data) < 2:
        return {"ticker": ticker, "error": "Insufficient data for return calculation"}
        
    entry_price = data['close'].iloc[0]
    exit_price = data['close'].iloc[-1]
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

