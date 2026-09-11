from pathlib import Path
import pandas as pd
from google.cloud import bigquery

# Locate the SQL file relative to this script
SKILL_DIR = Path(__file__).parent.parent
SQL_PATH = SKILL_DIR / "references" / "fetch_contract_signals.sql"

def get_bq_signals_data(ticker: str, analysis_date: str) -> list:
    """Internal: Runs the Contract Signals SQL Algorithm with Parameterized Query."""
    bq_client = bigquery.Client()
    
    if not SQL_PATH.exists():
        print(f"❌ SQL file missing at: {SQL_PATH}")
        return []

    qry = SQL_PATH.read_text(encoding="utf-8")
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
            bigquery.ScalarQueryParameter("analysis_date", "STRING", analysis_date)
        ]
    )
    
    try:
        df = bq_client.query(qry, job_config=job_config).to_dataframe()
    except Exception as e:
        print(f"❌ BigQuery Contract Signals Execution Error: {e}")
        return []
    
    if df.empty:
        return []

    # Fill null values to guarantee safety against Pydantic ContractSignalItem schema
    df['description'] = df['description'].fillna('No contract description provided.')
    df['amount'] = df['amount'].fillna(0.0)
    df['action_date'] = df['action_date'].astype(str)
    
    return df.to_dict(orient='records')