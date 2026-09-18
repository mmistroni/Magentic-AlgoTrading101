from pathlib import Path
from typing import List, Dict, Any, Optional
from google.cloud import bigquery

PROJECT_ID = "datascience-projects"

# Path to the SQL file in references/ directory
REFERENCES_DIR = Path(__file__).resolve().parents[2] / "references"
SQL_FILE_PATH = REFERENCES_DIR / "get_form4_signals.sql"


def get_bq_client() -> bigquery.Client:
    return bigquery.Client(project=PROJECT_ID)


def load_sql_query(file_path: Path) -> str:
    """Reads SQL query from file."""
    if not file_path.exists():
        raise FileNotFoundError(f"SQL reference file not found at: {file_path}")
    return file_path.read_text(encoding="utf-8")


def get_form4_data(
    analysis_date: str, 
    ticker: Optional[str] = None, 
    lookback_days: int = 90
) -> List[Dict[str, Any]]:
    """Loads get_form4_signals.sql and queries BigQuery for executive stock transactions.

    Args:
        analysis_date (str): Cutoff reference date in 'YYYY-MM-DD' format.
        ticker (str, optional): Target ticker symbol to filter results.
        lookback_days (int): Lookback window in days (default: 90).

    Returns:
        List[Dict[str, Any]]: List of dictionary records containing Form 4 metrics.
    """
    client = get_bq_client()
    query = load_sql_query(SQL_FILE_PATH)

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("analysis_date", "STRING", analysis_date),
            bigquery.ScalarQueryParameter("lookback_days", "INT64", lookback_days),
            bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
        ]
    )

    query_job = client.query(query, job_config=job_config)
    results = query_job.result()
    return [dict(row) for row in results]