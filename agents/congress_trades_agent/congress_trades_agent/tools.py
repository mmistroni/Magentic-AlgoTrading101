import json
import yfinance as yf
import pandas as pd
import numpy as np
from google.cloud import bigquery
from functools import lru_cache
from datetime import date
import requests
import os

def fetch_congress_signals_tool(analysis_date: str):
    """
    Fetches a list of Congress trades for the given month/date.
    Returns JSON list of tickers and transaction types.
    """
    # Mock data for demonstration
    signals = [
        {"ticker": "LMT", "rep": "Pelosi", "type": "Purchase", "amount": "500k"},
        {"ticker": "MSFT", "rep": "Tuberville", "type": "Sale", "amount": "100k"},
        {"ticker": "NVDA", "rep": "Unknown", "type": "Purchase", "amount": "50k"}
    ]
    return json.dumps(signals)

def check_fundamentals_tool(ticker: str):
    """
    Checks if a company is fundamentally sound.
    """
    return f"Fundamentals for {ticker}: Healthy balance sheet, Sector: Tech."


def _get_bq_data(analysis_date: str) -> pd.DataFrame:
    bq_client = bigquery.Client()
    qry = f"""
    -- -------------------------------
    -- CONFIG: Set @run_date to the last day of the month
    -- -------------------------------
    DECLARE run_date DATE DEFAULT DATE '{analysis_date}'; -- ← CHANGE THIS EVERY MONTH

    -- -------------------------------
    -- Step 1: Clean and parse trade data
    -- -------------------------------
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
        -- Only valid trades
        TICKER IS NOT NULL
        AND AS_OF_DATE IS NOT NULL
        -- Look back window: trades from last 90 days up to run_date
        AND AS_OF_DATE >= DATE_SUB(run_date, INTERVAL 90 DAY)
        AND AS_OF_DATE <= run_date
    )

    -- -------------------------------
    -- Step 2: Aggregate and score by ticker
    -- -------------------------------
    SELECT
        run_date AS signal_date,
        ticker,
        COUNTIF(action = 'Buy') AS purchase_count,
        COUNTIF(action = 'Sell') AS sale_count,
        (COUNTIF(action = 'Buy') - COUNTIF(action = 'Sell')) AS net_buy_activity,
        MAX(trade_date) AS last_trade_date,
        -- Rank within this month's screen
        ROW_NUMBER() OVER (
        ORDER BY
            (COUNTIF(action = 'Buy') - COUNTIF(action = 'Sell')) DESC,
            COUNTIF(action = 'Buy') DESC
        ) AS rank_in_month

    FROM clean_data

    WHERE
        -- Remove known ETFs, index funds, broad market noise
        LOWER(ticker) NOT IN (
        'vti', 'spy', 'voo', 'qqq', 'ivv', 'spxl', 'spxs',
        'tqqq', 'sqqq', 'dia', 'iwm', 'dow', 'shv', 'bnd'
        )
        -- Remove empty or invalid tickers
        AND TRIM(ticker) != ''
        AND ticker IS NOT NULL

    GROUP BY ticker, run_date

    -- -------------------------------
    -- Step 3: Apply High-Conviction Filters
    -- -------------------------------
    HAVING
        -- 1. Minimum net buying pressure
        net_buy_activity >= 15

        -- 2. Recent activity (trade in last ~3 months)
        AND last_trade_date >= DATE_SUB(run_date, INTERVAL 90 DAY)

        -- 3. Strong conviction: either no sells OR buy/sell ratio ≥ 2.0
        AND (
        COUNTIF(action = 'Sell') = 0
        OR
        (COUNTIF(action = 'Buy') * 1.0 / GREATEST(COUNTIF(action = 'Sell'), 1)) >= 2.0
        )

    -- -------------------------------
    -- Step 4: Limit output to top candidates
    -- -------------------------------
    ORDER BY
        net_buy_activity DESC,
        purchase_count DESC

    LIMIT 10; -- Get top 10 for flexibility; you can use top 5 in Python
    """
    df = bq_client.query(qry).to_dataframe()
    # Join with Market Regime

    return df.to_dict(orient='records')

def _check_market_regime(row_date:date)-> str:
    spy_data = _get_spy_data(date.today())
    try:
        # 🛠️ FIX 2: Force conversion to Timestamp and strip time/timezone
        target_date = pd.to_datetime(row_date).tz_localize(None)

        # Get the index of the latest available date <= target_date
        # "asof" is great but sometimes tricky with types.
        # Let's use get_indexer with method='pad' for robustness.
        idx_loc = spy_data.index.get_indexer([target_date], method='pad')[0]

        if idx_loc == -1: return True # Date is before our data starts

        # Access by integer location (iloc) which is safer here
        price = spy_data.iloc[idx_loc]['Adj Close']
        sma = spy_data.iloc[idx_loc]['SMA200']

        # Handle cases where data might be returned as Series (rare but possible)
        if isinstance(price, pd.Series): price = price.iloc[0]
        if isinstance(sma, pd.Series): sma = sma.iloc[0]

        # Check if NaN (e.g., start of dataset before 200 SMA exists)
        if pd.isna(sma): return True

        return price > sma

    except Exception as e:
        # If anything fails, print error but default to True (don't block trade)
        # print(f"Error checking regime: {e}")
        return True

def _get_spy_data(end_date:date) -> pd.DataFrame :
    fmp_api_key = os.environ['FMP_API_KEY']
    spx_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/^SPX?from=2024-01-01&to={date.today().strftime('%Y-%m-%d')}&apikey={fmp_api_key}"
    spx_res = requests.get(spx_url).json()['historical'][::-1]

    spy_data = pd.DataFrame(data=spx_res)
    # 🛠️ FIX 1: Ensure SPY Index is clean (remove timezone if present)
    spy_data.index = pd.to_datetime(spy_data.index).tz_localize(None)
    # 2. Calculate the 200-Day Moving Average
    spy_data['SMA200'] = spy_data['adjClose'].rolling(window=200).mean()
    return spy_data

