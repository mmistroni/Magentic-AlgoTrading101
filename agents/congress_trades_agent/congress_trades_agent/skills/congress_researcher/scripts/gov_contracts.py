from pathlib import Path
import pandas as pd
from google.cloud import bigquery

# Locate the SQL file relative to this script
SKILL_DIR = Path(__file__).parent.parent
SQL_PATH = SKILL_DIR / "references" / "fetch_contract_signals.sql"


def get_bq_signals_data(ticker: str, analysis_date: str) -> list[dict]:
    """Internal: Runs the Contract Signals SQL Algorithm with Parameterized Query."""
    bq_client = bigquery.Client()
    qry = SQL_PATH.read_text(encoding="utf-8")
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ticker", "STRING", str(ticker).upper()),
            bigquery.ScalarQueryParameter("analysis_date", "STRING", str(analysis_date)),
        ]
    )
    
    df = bq_client.query(qry, job_config=job_config).to_dataframe()
    
    if df.empty:
        return []

    # Format action_date to ISO string prior to returning dictionary records
    if "action_date" in df.columns:
        df["action_date"] = df["action_date"].astype(str)
    
    return df.to_dict(orient="records")