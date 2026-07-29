import os
from dataclasses import dataclass
from google.cloud import bigquery
import logging
from datetime import date, timedelta

import os
from google.cloud import bigquery
import google.auth

def get_bigquery_client():
    credentials, project = google.auth.default()
    return bigquery.Client(credentials=credentials, project=project)

def _get_table_schema():
    client = get_bigquery_client()
    
    # Use environment variables for your specific location
    dataset_id = 'gcp_shareloader'
    table_id = 'finviz-premarket'
    table_ref = f"{client.project}.{dataset_id}.{table_id}"

    logging.info(f'====TAbleREf={table_ref}|')
    table = client.get_table(table_ref)
    logging.info('===============Now getting ll fields')

    # We return a simple dict or string for the agent to parse
    return {field.name: field.field_type for field in table.schema}

def discover_technical_schema_tool():
    """Returns a list of available technical indicators and their types."""
    # SDK automatically pulls project from your environment/ADC
    print(f'[SCHEMA DISCOVERY] === Gettign schema...')
    return _get_table_schema()
    

from datetime import date, timedelta
from google.cloud import bigquery

def fetch_technical_snapshot_tool(target_date: str = "today") -> str:
    """
    Queries BigQuery for technical data for a specific day.
    Args:
        target_date: The date to query. Can be 'today', 'yesterday', or a date string 'YYYY-MM-DD'.
    """
    client = bigquery.Client()
    project = 'datascience-projects'
    dataset_id = 'gcp_shareloader'
    table_id = 'finviz-premarket'
    table_ref = f"{project}.{dataset_id}.{table_id}"
    
    print(f'Query tool: querying for {target_date}')

    # 1. Resolve target_date to a datetime.date object or formatted string
    if target_date.lower() == "today":
        resolved_date = date.today().strftime("%Y-%m-%d")
    elif target_date.lower() == "yesterday":
        resolved_date = (date.today() - timedelta(days=1)).strftime("%Y-%m-%d")
    else:
        resolved_date = target_date.strip()

    # 2. Query BigQuery safely with DATE casting
    # NOTE: Removed 'price is not null' because price is NULL in premarket datasets!
    query = f"""
        SELECT * FROM `{table_ref}`
        WHERE (DATE(cob) = DATE(@query_date) OR CAST(cob AS STRING) = @query_date)
          AND (open IS NOT NULL OR previousClose IS NOT NULL OR price IS NOT NULL)
    """
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("query_date", "STRING", resolved_date)
        ]
    )
    
    query_job = client.query(query, job_config=job_config)
    df = query_job.to_dataframe()
    
    if df.empty:
        return f"No data found for {resolved_date}."
    
    return df.to_json(orient="records")