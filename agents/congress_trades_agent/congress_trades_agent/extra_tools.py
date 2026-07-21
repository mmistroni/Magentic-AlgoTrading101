import json

import json
from google.cloud import bigquery

def fetch_form4_signals_tool(ticker: str, analysis_date: str) -> str:
    """
    Insider Alignment Validator: Retrieves recent Form 4 insider trading data (CEOs, Directors) for a specific ticker.
    
    Use this tool to check for 'The Triple Crown' (Congress + Corporate Lobbying + C-Suite Insiders all aligning).

    Args:
        ticker (str): The stock symbol (e.g., 'BE', 'MOH', 'NDAQ').
        analysis_date (str): The reference date in 'YYYY-MM-DD' format.

    Returns:
        str: A JSON string containing insider transaction details:
             - 'insider_title': Role of the insider (e.g., 'CEO', 'CFO', 'Director').
             - 'transaction_type': 'Buy' or 'Sell'.
             - 'shares': Number of shares transacted.
             - 'transaction_date': When the filing/trade occurred.
             - 'signal_strength': 'Strong Buy Confluence', 'Warning - Insider Dumping', or 'Neutral'.
    """
    print(f"🕵️ Fetching live Form 4 Insider trades for: {ticker} around {analysis_date}")
    
    client = bigquery.Client()
    
    # Query BigQuery schema matching your dataset structure
    query = """
    SELECT 
        ticker,
        COALESCE(
            officer_title, 
            IF(is_director, 'Director', NULL),
            IF(is_officer, 'Officer', NULL),
            'Insider'
        ) AS insider_title,
        UPPER(TRIM(transaction_side)) AS transaction_type,
        CAST(shares AS INT64) AS shares,
        CAST(filing_date AS STRING) AS transaction_date
    FROM 
        `datascience-projects.gcp_shareloader.form4_disclosures`
    WHERE 
        UPPER(TRIM(ticker)) = UPPER(@ticker)
        AND filing_date <= PARSE_DATE('%Y-%m-%d', @analysis_date)
        AND filing_date >= DATE_SUB(PARSE_DATE('%Y-%m-%d', @analysis_date), INTERVAL 90 DAY)
        AND UPPER(TRIM(transaction_side)) IN ('BUY', 'SELL')
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
            return json.dumps({
                "ticker": ticker.upper(),
                "error": "No recent insider transactions found.",
                "signal_strength": "Neutral"
            })
            
        row = dict(results[0].items())
        
        # Determine signal strength dynamically
        tx_type = str(row.get("transaction_type", "")).capitalize()
        title = str(row.get("insider_title", "")).upper()
        
        if tx_type == "Buy" and any(role in title for role in ["CEO", "CFO", "DIRECTOR", "OFFICER"]):
            signal = "Strong Buy Confluence"
        elif tx_type == "Sell" and any(role in title for role in ["CEO", "CFO"]):
            signal = "Warning - Insider Dumping"
        else:
            signal = "Neutral"
            
        row["signal_strength"] = signal
        row["transaction_type"] = tx_type
        
        return json.dumps(row)

    except Exception as e:
        print(f"❌ Error querying Form 4 data: {e}")
        return json.dumps({
            "ticker": ticker.upper(),
            "error": f"Failed to execute query: {str(e)}",
            "signal_strength": "Neutral"
        })


import json
from google.cloud import bigquery
import os

def fetch_lobbying_signals_tool(ticker: str):
    """
    Political Context Validator: Retrieves recent corporate lobbying activity for a specific ticker.
    
    Use this tool to find out if a company is actively spending money in Washington D.C., 
    how much they are spending, and what specific issues they are lobbying for.

    Args:
        ticker (str): The stock symbol (e.g., 'NVDA', 'LMT').

    Returns:
        str: A JSON string containing:
             - 'total_recent_spend': Sum of lobbying amounts.
             - 'recent_filing_dates': Dates of the lobbying reports.
             - 'lobbied_issues': A list of text describing what they lobbied for.
    """
    print(f"🏛️ Fetching corporate lobbying data for: {ticker}")
    
    try:
        # Initialize BigQuery Client
        project_id = os.environ.get("GOOGLE_CLOUD_PROJECT", "datascience-projects")
        client = bigquery.Client(project=project_id)
        
        # Query to get the last 12 months of lobbying for this ticker
        query = f"""
            SELECT 
                ticker,
                client_name,
                SUM(amount) as total_spend,
                MAX(filing_date) as latest_filing,
                STRING_AGG(DISTINCT general_issues LIMIT 5) as top_issues,
                COUNT(*) as number_of_filings
            FROM `datascience-projects.gcp_shareloader.lobbying_signals`
            WHERE ticker = @ticker
              -- Look at the last 365 days of available data
              AND filing_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 365 DAY)
            GROUP BY ticker, client_name
        """
        
        # Use query parameters for safety
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("ticker", "STRING", ticker.upper())
            ]
        )
        
        results = client.query(query, job_config=job_config).result()
        
        # Parse the result
        records = list(results)
        if not records:
            return json.dumps({
                "ticker": ticker, 
                "lobbying_status": "No recent lobbying activity found."
            })
            
        row = records[0]
        lobbying_data = {
            "ticker": row.ticker,
            "company_name": row.client_name,
            "total_spend_last_12m": float(row.total_spend) if row.total_spend else 0,
            "latest_filing_date": str(row.latest_filing),
            "number_of_filings": row.number_of_filings,
            "top_lobbied_issues": row.top_issues
        }
        
        return json.dumps(lobbying_data)

    except Exception as e:
        return json.dumps({"ticker": ticker, "error": f"Database error: {str(e)}"})