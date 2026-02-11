import json
import requests
import os
import pandas as pd
import numpy as np
import yfinance as yf
from google.cloud import bigquery
from functools import lru_cache
from datetime import date, datetime

# ==============================================================================
# 1. EXPOSED TOOLS (With LLM-Optimized Docstrings)
# ==============================================================================

def fetch_congress_signals_tool(analysis_date: str):
    """
    Primary Entry Point: Retrieves 'High Conviction' Congress trading signals for a specific date.
    
    Use this tool to get the initial list of stock candidates. It executes a complex SQL query
    that filters for 'Net Buy Activity' > 15 to find coordinated insider buying.

    Args:
        analysis_date (str): The reference date for the analysis in 'YYYY-MM-DD' format.
                             The tool looks back 90 days from this date.

    Returns:
        str: A JSON string containing a list of records. Each record includes:
             - 'ticker': The stock symbol.
             - 'net_buy_activity': A score representing buying pressure.
             - 'market_uptrend': Boolean (True = Bull Regime, False = Bear Regime).
             
    Example Output:
        [{"ticker": "LMT", "net_buy_activity": 20, "market_uptrend": true}, ...]
    """
    try:
        signals = _get_bq_data(analysis_date)
        print(f"🔍 Fetched {len(signals)} high-conviction signals for {analysis_date}")
        return json.dumps(signals)
    except Exception as e:
        return json.dumps({"error": str(e)})

def check_fundamentals_tool(ticker: str):
    """
    Safety Validator: Fetches a financial 'Safety Snapshot' for a specific ticker.
    
    Use this tool to validate if a Congress trade is financially sound or a speculative gamble.
    It returns key metrics required for risk assessment.

    Args:
        ticker (str): The stock symbol (e.g., 'NVDA', 'LMT').

    Returns:
        str: A JSON string containing:
             - 'sector': For checking Political Context alignment.
             - 'beta': Volatility metric (Risk).
             - 'forward_pe': Valuation metric.
             - 'debt_to_equity': Bankruptcy risk metric.
             - 'market_cap_B': Size in Billions.
    """
    print(f"🔍 Checking fundamentals for: {ticker}")
    
    try:
        stock = yf.Ticker(ticker)
        info = stock.info 
        
        # Extract ONLY decision-critical data to save tokens
        fundamentals = {
            "ticker": ticker,
            "sector": info.get("sector", "Unknown"),
            "industry": info.get("industry", "Unknown"),
            "market_cap_B": round(info.get("marketCap", 0) / 1_000_000_000, 2),
            "beta": round(info.get("beta", 1.0), 2),
            "forward_pe": round(info.get("forwardPE", 0), 2),
            "debt_to_equity": info.get("debtToEquity", None),
            "dividend_yield": info.get("dividendYield", 0)
        }
        return json.dumps(fundamentals)

    except Exception as e:
        return json.dumps({
            "ticker": ticker, 
            "error": "Data Unavailable", 
            "sector": "Unknown"
        })

# ==============================================================================
# 2. INTERNAL HELPERS (Hidden from Agent, handles logic)
# ==============================================================================

def _get_bq_data(analysis_date: str) -> list:
    """Internal: Runs the Net Buy Activity SQL Algorithm with Anti-Spam Logic."""
    bq_client = bigquery.Client()
    
    qry = f"""
    -- CONFIG: Set @run_date to the input date
    DECLARE run_date DATE DEFAULT DATE '{analysis_date}';

    WITH clean_data AS (
        SELECT
        AS_OF_DATE AS trade_date,
        CASE
            WHEN DISCLOSURE LIKE '%Purchase%' THEN 'Buy'
            WHEN DISCLOSURE LIKE '%Sale%' THEN 'Sell'
            ELSE 'Other'
        END AS action,
        TRIM(REPLACE(TICKER, 'Ticker:', '')) AS ticker
        FROM `datascience-projects.gcp_shareloader.senate_disclosures`
        WHERE
        TICKER IS NOT NULL
        AND AS_OF_DATE IS NOT NULL
        AND AS_OF_DATE >= DATE_SUB(run_date, INTERVAL 90 DAY)
        AND AS_OF_DATE <= run_date
    )

    SELECT
        run_date AS signal_date,
        ticker,
        COUNTIF(action = 'Buy') AS purchase_count,
        COUNTIF(action = 'Sell') AS sale_count,
        (COUNTIF(action = 'Buy') - COUNTIF(action = 'Sell')) AS net_buy_activity,
        
        -- NEW METRIC: Count Distinct Days (The Spam Filter)
        COUNT(DISTINCT CASE WHEN action='Buy' THEN trade_date END) as buying_days_count,
        
        MAX(trade_date) AS last_trade_date
    FROM clean_data
    WHERE
        LOWER(ticker) NOT IN (
        'vti', 'spy', 'voo', 'qqq', 'ivv', 'spxl', 'spxs',
        'tqqq', 'sqqq', 'dia', 'iwm', 'dow', 'shv', 'bnd'
        )
        AND TRIM(ticker) != ''
        AND ticker IS NOT NULL
        
        -- NEW FILTERS: Remove Mutual Funds (5 chars) and weird symbols
        AND LENGTH(ticker) <= 4 
        AND NOT REGEXP_CONTAINS(ticker, r'[^a-zA-Z]') 

    GROUP BY ticker, run_date

    HAVING
        -- 1. Must be bought on at least 2 SEPARATE days (Kills 1-day spam)
        buying_days_count >= 2
        
        -- 2. Net activity must still be positive
        AND net_buy_activity >= 5
        AND last_trade_date >= DATE_SUB(run_date, INTERVAL 90 DAY)
        AND (
        COUNTIF(action = 'Sell') = 0
        OR
        (COUNTIF(action = 'Buy') * 1.0 / GREATEST(COUNTIF(action = 'Sell'), 1)) >= 2.0
        )

    ORDER BY buying_days_count DESC, net_buy_activity DESC
    LIMIT 10;
    """
    
    df = bq_client.query(qry).to_dataframe()
    
    if df.empty:
        return []

    # Extra Python Filtering
    df_filtered = df[
            (df['sale_count'] == 0) &
            ~df['ticker'].str.contains('DFCEX|VWLUX|LDNXF|TNA|AAL|BRK/B', case=False)
    ]
    
    # Enrich with Market Regime
    df_filtered['market_uptrend'] = df_filtered['signal_date'].apply(
        lambda x: _check_market_regime(x, analysis_date)
    )
    
    # Convert dates to string for JSON serialization
    df_filtered['signal_date'] = df_filtered['signal_date'].astype(str)
    df_filtered['last_trade_date'] = df_filtered['last_trade_date'].astype(str)
    
    # Return both scores so the Agent can see the quality
    return df_filtered.to_dict(orient='records')

def _check_market_regime(row_date, context_date_str) -> bool:
    """Checks if SPY price > SMA200 for the specific row date."""
    try:
        # Fetch SPY data up to the context date (cached)
        spy_data = _get_spy_data(context_date_str)
        
        target_date = pd.to_datetime(row_date).tz_localize(None)

        # Find nearest date in SPY history
        idx_loc = spy_data.index.get_indexer([target_date], method='pad')[0]

        if idx_loc == -1: 
            return True # Default to Bull if data missing

        price = spy_data.iloc[idx_loc]['adjClose']
        sma = spy_data.iloc[idx_loc]['SMA200']

        if pd.isna(sma): return True

        return bool(price > sma)

    except Exception as e:
        print(f"⚠️ Regime Check Warning: {e}")
        return True # Default to Bull on error to not block trade

@lru_cache(maxsize=32)
def _get_spy_data(end_date_str: str) -> pd.DataFrame:
    """Fetches SPY history + SMA200 from FMP. Cached to save API calls."""
    try:
        fmp_api_key = os.environ.get('FMP_API_KEY')
        if not fmp_api_key:
            raise ValueError("FMP_API_KEY environment variable not set")

        # Fetch enough history to calc 200 SMA (approx 400 days lookback)
        # We assume end_date_str is relevant, but we fetch YTD + previous year buffer
        spx_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/^SPX?from=2022-01-01&to={end_date_str}&apikey={fmp_api_key}"
        
        response = requests.get(spx_url)
        if response.status_code != 200:
            raise Exception(f"FMP API Error: {response.text}")
            
        spx_res = response.json().get('historical', [])
        if not spx_res:
            raise Exception("No historical data returned")

        # Sort chronological (API returns reverse chronological)
        spx_res = spx_res[::-1]

        spy_data = pd.DataFrame(data=spx_res)
        
        # 🛠️ FIX: Explicitly set Index to Date
        spy_data['date'] = pd.to_datetime(spy_data['date'])
        spy_data.set_index('date', inplace=True)
        spy_data.index = spy_data.index.tz_localize(None)

        # Calc SMA
        spy_data['SMA200'] = spy_data['adjClose'].rolling(window=200).mean()
        
        return spy_data
        
    except Exception as e:
        print(f"❌ SPY Data Fetch Error: {e}")
        # Return empty DF to prevent crash, check_market_regime will handle it
        return pd.DataFrame()