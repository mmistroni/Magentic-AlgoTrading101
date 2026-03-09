import json

def fetch_form4_signals_tool(ticker: str, analysis_date: str):
    """
    Insider Alignment Validator: Retrieves recent Form 4 insider trading data (CEOs, Directors) for a specific ticker.
    
    Use this tool to check for 'The Triple Crown' (Congress + Corporate Lobbying + C-Suite Insiders all aligning).
    It uses mocked data for backtesting purposes.

    Args:
        ticker (str): The stock symbol (e.g., 'BE', 'MOH', 'NDAQ').
        analysis_date (str): The reference date in 'YYYY-MM-DD' format.

    Returns:
        str: A JSON string containing insider transaction details:
             - 'insider_title': Role of the insider (e.g., 'CEO', 'CFO').
             - 'transaction_type': 'Buy' or 'Sell'.
             - 'shares': Number of shares transacted.
             - 'transaction_date': When the trade occurred.
             - 'signal_strength': 'Strong', 'Neutral', or 'Warning'.
    """
    print(f"🕵️ Checking Form 4 Insider trades for: {ticker} around {analysis_date}")
    
    # Mocked database for our test cases
    mock_form4_db = {
        "BE": {
            "ticker": "BE",
            "insider_title": "CEO", 
            "transaction_type": "Buy", 
            "shares": 25000, 
            "transaction_date": "2024-10-25",
            "signal_strength": "Strong Buy Confluence"
        },
        "MOH": {
            "ticker": "MOH",
            "insider_title": "CFO", 
            "transaction_type": "Sell", 
            "shares": 15000, 
            "transaction_date": "2024-06-05",
            "signal_strength": "Warning - Insider Dumping"
        },
        "NDAQ": {
            "ticker": "NDAQ",
            "insider_title": "Director", 
            "transaction_type": "Hold", 
            "shares": 0, 
            "transaction_date": "N/A",
            "signal_strength": "Neutral"
        }
    }
    
    # Fetch data or return a default empty state if ticker not in mock DB
    insider_data = mock_form4_db.get(ticker.upper(), {
        "ticker": ticker,
        "error": "No recent insider transactions found.",
        "signal_strength": "Neutral"
    })
    
    return json.dumps(insider_data)


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