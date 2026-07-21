import json
import os
from typing import Optional
from google.cloud import bigquery
from congress_trades_agent.schemas import LobbyingSignalResponse
import json
from google.cloud import bigquery
from .schemas import Form4SignalResponse, FundamentalsResponse

# 2. Refactor tool signature and return type
def fetch_form4_signals_tool(ticker: str, analysis_date: str) -> Form4SignalResponse:
    """
    Insider Alignment Validator: Retrieves recent Form 4 insider trading data for a specific ticker.
    Checks `form4_master` table schema using boolean flags (is_officer, is_director) and officer_title.
    """
    print(f"🕵️ Fetching live Form 4 Insider trades for: {ticker} around {analysis_date}")
    
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
            bigquery.ScalarQueryParameter("ticker", "STRING", ticker.strip().upper()),
            bigquery.ScalarQueryParameter("analysis_date", "STRING", analysis_date),
        ]
    )
    
    try:
        query_job = client.query(query, job_config=job_config)
        results = list(query_job.result())
        
        if not results:
            return Form4SignalResponse(
                ticker=ticker.upper(),
                error="No recent insider transactions found.",
                signal_strength="Neutral"
            )
            
        row = dict(results[0].items())
        
        # Normalize transaction side ('P' or 'BUY' -> Buy, 'S' or 'SELL' -> Sell)
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
        
        # Robust executive role evaluation
        EXEC_KEYWORDS = ["CEO", "CFO", "CHIEF", "EXECUTIVE", "PRESIDENT", "VP", "OFFICER", "DIRECTOR"]
        is_key_executive = is_officer or is_director or any(kw in title for kw in EXEC_KEYWORDS)
        
        if tx_type == "Buy" and is_key_executive:
            signal = "Strong Buy Confluence"
        elif tx_type == "Sell" and is_key_executive:
            signal = "Warning - Insider Dumping"
        else:
            signal = "Neutral"
            
        return Form4SignalResponse(
            ticker=ticker.upper(),
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
            ticker=ticker.upper(),
            error=f"Failed to execute query: {str(e)}",
            signal_strength="Neutral"
        )


# congress_trades_agent/extra_tools.py

def fetch_lobbying_signals_tool(ticker: str, analysis_date: Optional[str] = None) -> LobbyingSignalResponse:
    """
    Political Context Validator: Retrieves recent corporate lobbying activity for a specific ticker.
    Returns a validated LobbyingSignalResponse Pydantic object.

    Args:
        ticker (str): The stock symbol (e.g., 'NVDA', 'LMT').
        analysis_date (Optional[str]): Reference date in 'YYYY-MM-DD' format. Defaults to current date if None.
    """
    clean_ticker = ticker.strip().upper()
    print(f"🏛️ Fetching corporate lobbying data for: {clean_ticker}")
    
    try:
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "datascience-projects")
        client = bigquery.Client(project=project_id)
        
        # SQL with parameterized analysis date logic
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
        
        # Parse aggregated issues into a clean Python list
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