import os
from google.cloud import bigquery
from typing import List
from schemas import ClinicalSignalRecord

def load_sql_query(file_path: str) -> str:
    """Reads the SQL query from the resources directory."""

    # Gets the directory where the current script lives (e.g., /app or /app/skills/bq_scout)
    current_dir = os.path.dirname(os.path.abspath(__file__))
    # Safely construct the path relative to the script
    sql_path = os.path.join(current_dir, "resources", "bq.sql")
    with open(sql_path, "r") as f:
        return f.read()

def fetch_negative_clinical_signals(project_id: str, dataset_id: str, table_id: str) -> List[ClinicalSignalRecord]:
    """
    Queries BigQuery using the SQL template stored in resources/bq.sql.
    """
    client = bigquery.Client(project=project_id)
    
    # Path relative to the script or project root
    sql_path = os.path.join("resources", "bq.sql")
    raw_query = load_sql_query(sql_path)
    
    # Format the query with the target table reference if needed, 
    # or ensure your bq.sql handles table referencing dynamically.
    query = raw_query.format(
        project_id=project_id,
        dataset_id=dataset_id,
        table_id=table_id
    )
    
    query_job = client.query(query)
    results = query_job.result()
    
    records = []
    for row in results:
        record = ClinicalSignalRecord(
            scraped_at=row.scraped_at,
            nct_id=row.nct_id,
            sponsor=row.sponsor,
            title=row.title,
            status=row.status,
            negative_reason=row.negative_reason
        )
        records.append(record)
        
    return records