import os
from google.cloud import bigquery
from typing import List
from schemas import ClinicalSignalRecord

def load_sql_query() -> str:
    """Reads the SQL query from the resources/bq.sql directory relative to this script."""
    current_dir = os.path.dirname(os.path.abspath(__file__))
    sql_path = os.path.join(current_dir, "resources", "bq.sql")
    with open(sql_path, "r") as f:
        return f.read()

def fetch_negative_clinical_signals(project_id: str, dataset_id: str, table_id: str) -> List[ClinicalSignalRecord]:
    """
    Queries BigQuery using the SQL template stored in resources/bq.sql 
    and returns a list of validated ClinicalSignalRecord objects.
    """
    client = bigquery.Client(project=project_id)
    
    raw_query = load_sql_query()
    
    # Format the query with dynamic project, dataset, and table references
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
            ticker=row.ticker,
            cusip=row.cusip,
            sponsor=row.sponsor,
            failure_status=row.failure_status,
            failure_post_date=row.failure_post_date,
            nct_id=row.nct_id,
            trial_title=row.trial_title,
            failure_reason=row.failure_reason
        )
        records.append(record)
        
    return records