import os
import requests
import pandas as pd
import yfinance as yf
from typing import Optional
from functools import lru_cache
from google.cloud import bigquery

from congress_trades_agent.schemas import (
    CongressSignalItem,
    CongressSignalsResponse,
    FundamentalsResponse,
    Form4SignalResponse,
    LobbyingSignalResponse,
)

# Set persistent writable directory across local containers, AWS, and Cloud environments
yf.set_tz_cache_location("/tmp/py-yfinance")


# ==============================================================================
# EXPOSED AGENT TOOLS
# ==============================================================================

def fetch_congress_signals_tool(analysis_date: str) -> CongressSignalsResponse:
    """
    Primary Entry Point: Retrieves 'High Conviction' Congress trading signals for a specific date.
    
    Use this tool to obtain initial stock candidates based on insider Congress trading activity.
    It executes a query filtering for positive net buy activity (at least 2 buying days) over 
    a 90-day lookback window to identify coordinated insider buying while filtering out spammed trades.

    Args:
        analysis_date (str): The reference date for the analysis in 'YYYY-MM-DD' format.
                             The query looks back 90 days from this date.

    Returns:
        CongressSignalsResponse: Structured object containing:
            - analysis_date (str): Reference date queried.
            - signals (List[CongressSignalItem]): List of matching high-conviction trades,
              each with ticker, buy/sell counts, net buy activity, and market_uptrend regime status.
            - count (int): Total count of signals returned.
            - error (Optional[str]): Error message if execution fails.
    """
    try:
        raw_signals = _get_bq_data(analysis_date)
        print(f"🔍 Fetched {len(raw_signals)} high-conviction signals for {analysis_date}")
        
        signal_items = [CongressSignalItem(**item) for item in raw_signals]
        return CongressSignalsResponse(
            analysis_date=analysis_date,
            signals=signal_items,
            count=len(signal_items),
        )
    except Exception as e:
        print(f"❌ Error fetching congress signals: {e}")
        return CongressSignalsResponse(
            analysis_date=analysis_date,
            error=str(e),
        )


def check_fundamentals_tool(ticker: str) -> FundamentalsResponse:
    """
    Safety Validator: Fetches a financial 'Safety Snapshot' for a specific ticker using yfinance.
    
    Use this tool to validate whether a Congress trade candidate is financially sound or 
    speculative. Retrieves sector alignment, market cap, beta volatility, valuation (PE), 
    and leverage metrics.

    Args:
        ticker (str): The stock symbol (e.g., 'NVDA', 'LMT').

    Returns:
        FundamentalsResponse: Structured object containing:
            - ticker (str): Stock symbol.
            - sector (str): Company sector for political context alignment.
            - industry (str): Company industry classification.
            - market_cap_B (float): Market capitalization in billions.
            - beta (float): Volatility metric relative to market.
            - forward_pe (float): Valuation metric.
            - debt_to_equity (Optional[float]): Leverage/risk metric.
            - dividend_yield (float): Annual dividend yield percentage.
            - error (Optional[str]): Error details if data fetch fails.
    """
    clean_ticker = ticker.strip().upper()
    print(f"🔍 Checking fundamentals for: {clean_ticker}")
    
    try:
        stock = yf.Ticker(clean_ticker)
        info = stock.info or {}
        
        return FundamentalsResponse(
            ticker=clean_ticker,
            sector=info.get("sector", "Unknown"),
            industry=info.get("industry", "Unknown"),
            market_cap_B=round((info.get("marketCap") or 0) / 1_000_000_000, 2),
            beta=round(info.get("beta") or 1.0, 2),
            forward_pe=round(info.get("forwardPE") or 0.0, 2),
            debt_to_equity=info.get("debtToEquity"),
            dividend_yield=info.get("dividendYield") or 0.0,
        )

    except Exception as e:
        print(f"❌ Error fetching fundamentals for {clean_ticker}: {e}")
        return FundamentalsResponse(
            ticker=clean_ticker,
            error="Data Unavailable",
            sector="Unknown",
        )


def fetch_form4_signals_tool(ticker: str, analysis_date: str) -> Form4SignalResponse:
    """
    Insider Alignment Validator: Retrieves recent Form 4 insider trading data for a specific ticker.
    Checks `form4_master` table using boolean flags (is_officer, is_director) and officer_title.

    Args:
        ticker (str): Stock ticker symbol.
        analysis_date (str): Reference date in 'YYYY-MM-DD' format.

    Returns:
        Form4SignalResponse: Structured insider signal evaluation.
    """
    clean_ticker = ticker.strip().upper()
    print(f"🕵️ Fetching live Form 4 Insider trades for: {clean_ticker} around {analysis_date}")
    
    client = bigquery.Client()
    
    query = """
    SELECT 
        ticker,
        COALESCE(
            officer_title, 
            IF(is_director, 'Director', NULL),
            IF(is_officer, 'Officer', NULL),
            'Insider'
        ) AS insider_title,
        COALESCE(is_officer, FALSE) AS is_officer,
        COALESCE(is_director, FALSE) AS is_director,
        UPPER(TRIM(transaction_side)) AS transaction_type,
        CAST(shares AS INT64) AS shares,
        CAST(filing_date AS STRING) AS transaction_date
    FROM 
        `datascience-projects.gcp_shareloader.form4_master`
    WHERE 
        UPPER(TRIM(ticker)) = UPPER(@ticker)
        AND filing_date <= PARSE_DATE('%Y-%m-%d', @analysis_date)
        AND filing_date >= DATE_SUB(PARSE_DATE('%Y-%m-%d', @analysis_date), INTERVAL 90 DAY)
        AND UPPER(TRIM(transaction_side)) IN ('BUY', 'SELL', 'P', 'S')
    ORDER BY 
        filing_date DESC, shares DESC
    LIMIT 1;
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ticker", "STRING", clean_ticker),
            bigquery.ScalarQueryParameter("analysis_date", "STRING", analysis_date),
        ]
    )
    
    try:
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if not results:
            return Form4SignalResponse(
                ticker=clean_ticker,
                error="No recent insider transactions found.",
                signal_strength="Neutral"
            )
            
        row = dict(results[0].items())
        
        side_raw = str(row.get("transaction_type", "")).upper()
        if side_raw in ["BUY", "P"]:
            tx_type = "Buy"
        elif side_raw in ["SELL", "S"]:
            tx_type = "Sell"
        else:
            tx_type = side_raw.capitalize()

        title = str(row.get("insider_title", "")).upper()
        is_officer = bool(row.get("is_officer", False))
        is_director = bool(row.get("is_director", False))
        
        EXEC_KEYWORDS = ["CEO", "CFO", "CHIEF", "EXECUTIVE", "PRESIDENT", "VP", "OFFICER", "DIRECTOR"]
        is_key_executive = is_officer or is_director or any(kw in title for kw in EXEC_KEYWORDS)
        
        if tx_type == "Buy" and is_key_executive:
            signal = "Strong Buy Confluence"
        elif tx_type == "Sell" and is_key_executive:
            signal = "Warning - Insider Dumping"
        else:
            signal = "Neutral"
            
        return Form4SignalResponse(
            ticker=clean_ticker,
            insider_title=row.get("insider_title", "Insider"),
            transaction_type=tx_type,
            shares=row.get("shares", 0),
            transaction_date=str(row.get("transaction_date", "N/A")),
            is_officer=is_officer,
            is_director=is_director,
            signal_strength=signal
        )

    except Exception as e:
        print(f"❌ Error querying form4_master: {e}")
        return Form4SignalResponse(
            ticker=clean_ticker,
            error=f"Failed to execute query: {str(e)}",
            signal_strength="Neutral"
        )


def fetch_lobbying_signals_tool(ticker: str, analysis_date: Optional[str] = None) -> LobbyingSignalResponse:
    """
    Political Context Validator: Retrieves recent corporate lobbying activity for a specific ticker.
    
    Use this tool to find out if a company is actively spending money in Washington D.C., 
    how much they are spending, and what specific issues they are lobbying for.

    Args:
        ticker (str): The stock symbol (e.g., 'NVDA', 'LMT').
        analysis_date (Optional[str]): Reference date in 'YYYY-MM-DD' format. Defaults to current date if None.

    Returns:
        LobbyingSignalResponse: Structured lobbying metrics and top issues list.
    """
    clean_ticker = ticker.strip().upper()
    print(f"🏛️ Fetching corporate lobbying data for: {clean_ticker}")
    
    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "datascience-projects")
        client = bigquery.Client(project=project_id)
        
        query = """
            SELECT 
                ticker,
                client_name,
                SUM(amount) as total_spend,
                MAX(filing_date) as latest_filing,
                STRING_AGG(DISTINCT general_issues, ' | ') as raw_issues,
                COUNT(*) as number_of_filings
            FROM `datascience-projects.gcp_shareloader.lobbying_signals`
            WHERE UPPER(TRIM(ticker)) = UPPER(@ticker)
              AND filing_date <= IFNULL(PARSE_DATE('%Y-%m-%d', @analysis_date), CURRENT_DATE())
              AND filing_date >= DATE_SUB(IFNULL(PARSE_DATE('%Y-%m-%d', @analysis_date), CURRENT_DATE()), INTERVAL 365 DAY)
            GROUP BY ticker, client_name
            LIMIT 1;
        """
        
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("ticker", "STRING", clean_ticker),
                bigquery.ScalarQueryParameter("analysis_date", "STRING", analysis_date),
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        records = list(query_job.result())
        
        if not records:
            return LobbyingSignalResponse(
                ticker=clean_ticker,
                lobbying_status="No recent lobbying activity found."
            )
            
        row = dict(records[0].items())
        raw_issues = row.get("raw_issues") or ""
        issues_list = [issue.strip() for issue in raw_issues.split(" | ") if issue.strip()]
        
        return LobbyingSignalResponse(
            ticker=clean_ticker,
            company_name=row.get("client_name", "N/A"),
            total_spend_last_12m=float(row.get("total_spend") or 0.0),
            latest_filing_date=str(row.get("latest_filing", "N/A")),
            number_of_filings=int(row.get("number_of_filings") or 0),
            top_lobbied_issues=issues_list,
            lobbying_status="Active Lobbying Detected"
        )

    except Exception as e:
        print(f"❌ Error fetching lobbying signals: {e}")
        return LobbyingSignalResponse(
            ticker=clean_ticker,
            lobbying_status="Error",
            error=f"Database error: {str(e)}"
        )


# ==============================================================================
# INTERNAL HELPERS
# ==============================================================================

def _get_bq_data(analysis_date: str) -> list:
    """Internal: Runs the Net Buy Activity SQL Algorithm with Parameterized Query."""
    bq_client = bigquery.Client()
    
    qry = """
    DECLARE run_date DATE DEFAULT PARSE_DATE('%Y-%m-%d', @analysis_date);

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
        AND LENGTH(ticker) <= 4 
        AND NOT REGEXP_CONTAINS(ticker, r'[^a-zA-Z]') 
    GROUP BY ticker, run_date
    HAVING
        buying_days_count >= 2
        AND net_buy_activity >= 5
        AND last_trade_date >= DATE_SUB(run_date, INTERVAL 90 DAY)
        AND (
            COUNTIF(action = 'Sell') = 0
            OR (COUNTIF(action = 'Buy') * 1.0 / GREATEST(COUNTIF(action = 'Sell'), 1)) >= 2.0
        )
    ORDER BY buying_days_count DESC, net_buy_activity DESC
    LIMIT 10;
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("analysis_date", "STRING", analysis_date)
        ]
    )
    
    df = bq_client.query(qry, job_config=job_config).to_dataframe()
    
    if df.empty:
        return []

    df_filtered = df[
        (df['sale_count'] == 0) &
        ~df['ticker'].str.contains('DFCEX|VWLUX|LDNXF|TNA|AAL|BRK/B', case=False, na=False)
    ].copy()
    
    if df_filtered.empty:
        return []

    df_filtered['market_uptrend'] = df_filtered['signal_date'].apply(
        lambda x: _check_market_regime(x, analysis_date)
    )
    
    df_filtered['signal_date'] = df_filtered['signal_date'].astype(str)
    df_filtered['last_trade_date'] = df_filtered['last_trade_date'].astype(str)
    
    return df_filtered.to_dict(orient='records')


def _check_market_regime(row_date, context_date_str) -> bool:
    try:
        spy_data = _get_spy_data(context_date_str)
        if spy_data.empty:
            return True

        target_date = pd.to_datetime(row_date).tz_localize(None)
        idx_loc = spy_data.index.get_indexer([target_date], method='pad')[0]

        if idx_loc == -1: 
            return True

        price = spy_data.iloc[idx_loc]['adjClose']
        sma = spy_data.iloc[idx_loc]['SMA200']

        if pd.isna(sma):
            return True

        return bool(price > sma)

    except Exception as e:
        print(f"⚠️ Regime Check Warning: {e}")
        return True


@lru_cache(maxsize=32)
def _get_spy_data(end_date_str: str) -> pd.DataFrame:
    try:
        fmp_api_key = os.environ.get('FMP_API_KEY')
        if not fmp_api_key:
            return pd.DataFrame()

        spx_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/^SPX?from=2022-01-01&to={end_date_str}&apikey={fmp_api_key}"
        response = requests.get(spx_url, timeout=10)
        
        if response.status_code != 200:
            return pd.DataFrame()
            
        spx_res = response.json().get('historical', [])
        if not spx_res:
            return pd.DataFrame()

        spx_res = spx_res[::-1]
        spy_data = pd.DataFrame(data=spx_res)
        
        spy_data['date'] = pd.to_datetime(spy_data['date'])
        spy_data.set_index('date', inplace=True)
        spy_data.index = spy_data.index.tz_localize(None)
        spy_data['SMA200'] = spy_data['adjClose'].rolling(window=200).mean()
        
        return spy_data
        
    except Exception as e:
        print(f"❌ SPY Data Fetch Error: {e}")
        return pd.DataFrame()