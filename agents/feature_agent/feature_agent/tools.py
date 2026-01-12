from datetime import date, timedelta
import yfinance as yf
from google import genai
from google.genai import types
import os
import requests
import pandas as pd
from google.cloud import bigquery


# --- TOOL 1: BigQuery Historical Consensus ---
def fetch_consensus_holdings_tool(target_date: str) -> list:
    """
    Finds the high-conviction 'Elite' picks by running the Sniping Query 
    for a specific quarter-end date.
    """
    # This matches your exact logic from yesterday
    query = f"""
                SELECT 
                map.ticker,
                MAX(base.issuer_name) as issuer_name,
                COUNT(DISTINCT base.manager_name) as manager_count
            FROM (
                SELECT 
                    manager_name, 
                    cusip, 
                    issuer_name, 
                    ROW_NUMBER() OVER(PARTITION BY manager_name, filing_date ORDER BY value_usd DESC) as position_rank
                FROM `datascience-projects.gcp_shareloader.all_holdings_master`
                WHERE manager_name IN (
                    SELECT manager_name FROM `datascience-projects.gcp_shareloader.high_conviction_master`
                    WHERE manager_tier = 'TIER_1_ELITE'
                )
                AND filing_date = '{target_date}'
            ) base
            JOIN `datascience-projects.gcp_shareloader.map_cusip_ticker` map 
            ON base.cusip = map.cusip
            WHERE base.position_rank <= 10
            -- KEEP THE FILTERS HERE:
            AND UPPER(base.issuer_name) NOT LIKE '% ETF%'
            AND UPPER(base.issuer_name) NOT LIKE '% INDEX%'
            AND UPPER(base.issuer_name) NOT LIKE '% TRUST%'
            AND UPPER(base.issuer_name) NOT LIKE '% SPDR%'
            AND UPPER(base.issuer_name) NOT LIKE '% ISHARES%'
            AND UPPER(base.issuer_name) NOT LIKE '% VANGUARD%'
            GROUP BY 1
            HAVING manager_count >= 3
            ORDER BY manager_count DESC;
    """
    # Assuming bq_client is initialized
    bq_client = bigquery.Client()
    
    df = bq_client.query(query).to_dataframe()
    return df.to_dict(orient='records')
    

# --- TOOL 2: Technical Confirmation (yfinance) ---
def get_technical_metrics_tool(ticker: str, target_date: str) -> dict:
    """Verifies if the stock was above 200DMA on the 45-day public date."""
    fmp_key = os.environ['FMP_KEY']
    public_date = date.fromisoformat(target_date) + timedelta(days=45)
    data = yf.download(ticker, start=public_date - timedelta(days=300), end=public_date)
    
    current_price = data['Close'].iloc[-1]
    sma_200 = data['Close'].rolling(window=200).mean().iloc[-1]
    
    return {
        "ticker": ticker,
        "is_above_200dma": bool(current_price > sma_200),
        "price_at_entry": float(current_price)
    }

# --- TOOL 3: Performance Audit ---
def get_forward_return_tool(ticker: str, entry_date: str, days_ahead: int = 180) -> dict:
    """Calculates the ROI after a specific holding period (e.g., 6 months)."""
    start = date.fromisoformat(entry_date) + timedelta(days=45)
    end = start + timedelta(days=days_ahead)
    data = yf.download(ticker, start=start, end=end + timedelta(days=5))
    
    entry_price = data['Close'].iloc[0]
    exit_price = data['Close'].iloc[-1]
    return {"ticker": ticker, "return_pct": float((exit_price - entry_price) / entry_price * 100)}


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

# 2. Define Tool Schemas for Google SDK
feature_tools = [
    types.FunctionDeclaration(
        name="fetch_consensus_holdings_tool",
        description="Fetch historical top picks from Elite Managers.",
        parameters={
            "type": "OBJECT",
            "properties": {"target_date": {"type": "STRING", "description": "YYYY-MM-DD"}},
            "required": ["target_date"]
        }
    ),
    types.FunctionDeclaration(
        name="get_technical_metrics_tool",
        description="Check if a ticker was above its 200-day moving average.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "ticker": {"type": "STRING"},
                "target_date": {"type": "STRING"}
            },
            "required": ["ticker", "target_date"]
        }
    ),
    types.FunctionDeclaration(
        name="get_forward_return_tool",
        description="Calculate the performance of a pick after 6 months.",
        parameters={
            "type": "OBJECT",
            "properties": {
                "ticker": {"type": "STRING"},
                "entry_date": {"type": "STRING"}
            },
            "required": ["ticker", "entry_date"]
        }
    )
]

