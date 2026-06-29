import os
from typing import List, Dict, Any
from google.cloud import bigquery

PROJECT_ID = os.environ.get("PROJECT_ID", "datascience-projects")
DATASET_ID = "gcp_shareloader"
TABLE_ID = "biotech_catalysts"

def store_catalysts_in_bigquery(records: List[Dict[str, Any]]):
    """
    Appends the parsed catalyst records into your BigQuery dataset destination table.
    """
    if not records:
        print("⚠️ [Storage] No records provided to append. Aborting BigQuery call.")
        return
        
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    
    # Declare structural type safe tracking fields 
    schema = [
        bigquery.SchemaField("scraped_at", "TIMESTAMP"),
        bigquery.SchemaField("nct_id", "STRING"),
        bigquery.SchemaField("sponsor", "STRING"),
        bigquery.SchemaField("title", "STRING"),
        bigquery.SchemaField("status", "STRING"),
        bigquery.SchemaField("negative_reason", "STRING", mode="NULLABLE"),
    ]
    
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_APPEND"
    )
    
    print(f"📦 [Storage] Upserting {len(records)} records to {table_ref}...")
    try:
        job = client.load_table_from_json(records, table_ref, job_config=job_config)
        job.result()  # Blocks until execution thread completes
        print("✅ [Storage Complete] BigQuery write transaction succeeded.")
    except Exception as e:
        print(f"❌ [Storage Error] Failed writing data payloads to BigQuery: {e}")