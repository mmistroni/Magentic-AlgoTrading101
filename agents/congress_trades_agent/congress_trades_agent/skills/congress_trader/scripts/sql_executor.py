import os
from pathlib import Path
from google.cloud import bigquery
from typing import Optional

# Initialize BigQuery client
bq_client = bigquery.Client()

DATASET_ID = os.getenv("BQ_DATASET_ID", "gcp_shareloader")
TABLE_ID = os.getenv("BQ_TABLE_ID", "trade_decisions")
FULL_TABLE_REF = f"{bq_client.project}.{DATASET_ID}.{TABLE_ID}"

QUERIES_DIR = Path(__file__).parent / "queries"

def _load_sql(filename: str) -> str:
    """Helper to load a SQL query template from the queries directory."""
    return (QUERIES_DIR / filename).read_text(encoding="utf-8")

def execute_store_decision(
    decision_id: str,
    ticker: str,
    decision_timestamp: str,
    action: str,
    conviction_score: float,
    decision_snapshot_json: str
) -> None:
    """Executes the store decision SQL script."""
    sql_template = _load_sql("store_decision.sql")
    query = sql_template.format(table_ref=FULL_TABLE_REF)
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("decision_id", "STRING", decision_id),
            bigquery.ScalarQueryParameter("ticker", "STRING", ticker.upper()),
            bigquery.ScalarQueryParameter("decision_timestamp", "STRING", decision_timestamp),
            bigquery.ScalarQueryParameter("action", "STRING", action),
            bigquery.ScalarQueryParameter("conviction_score", "FLOAT64", conviction_score),
            bigquery.ScalarQueryParameter("decision_snapshot_json", "STRING", decision_snapshot_json),
        ]
    )
    
    query_job = bq_client.query(query, job_config=job_config)
    query_job.result() # Wait for execution completion

def execute_fetch_decisions(
    ticker: Optional[str] = None,
    valuation_verdict: Optional[str] = None,
    min_conviction: Optional[float] = None,
    limit: int = 5
) -> bigquery.table.RowIterator:
    """Executes the fetch historical decisions SQL script."""
    sql_template = _load_sql("fetch_decisions.sql")
    query = sql_template.format(table_ref=FULL_TABLE_REF)
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("ticker", "STRING", ticker.upper() if ticker else None),
            bigquery.ScalarQueryParameter("val_verdict", "STRING", valuation_verdict.upper() if valuation_verdict else None),
            bigquery.ScalarQueryParameter("min_conviction", "FLOAT64", min_conviction),
            bigquery.ScalarQueryParameter("limit", "INT64", limit),
        ]
    )
    
    query_job = bq_client.query(query, job_config=job_config)
    return query_job.result()