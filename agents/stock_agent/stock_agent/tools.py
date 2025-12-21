import os
from dataclasses import dataclass
from google.cloud import bigquery

import os
from google.cloud import bigquery

def discover_technical_schema_tool():
    """Returns a list of available technical indicators and their types."""
    # SDK automatically pulls project from your environment/ADC
    client = bigquery.Client()
    
    # Use environment variables for your specific location
    dataset_id = 'gcp_shareloader'
    table_id = 'finviz-premarket'
    table_ref = f"{client.project}.{dataset_id}.{table_id}"

    print(f'====TAbleREf={table_ref}|')


    table = client.get_table(table_ref)
    
    print('===============Now getting ll fields')

    # We return a simple dict or string for the agent to parse
    return {field.name: field.field_type for field in table.schema}

def fetch_today_technical_snapshot_tool():
    """Queries BigQuery for the current day's technical data."""
    client = bigquery.Client()
    dataset_id = 'gcp_shareloader'
    table_id = 'finviz-premarket'
    table_ref = f"{client.project}.{dataset_id}.{table_id}"

    # Standard SQL using CURRENT_DATE() for the snapshot
    query = f"""
        SELECT * FROM `{table_ref}`
        WHERE date = CURRENT_DATE()
    """
    
    # to_dataframe() is the most efficient way to pass data to an LLM
    query_job = client.query(query)
    df = query_job.to_dataframe()
    
    if df.empty:
        return "No data loaded for today yet."
    
    return df.to_json(orient="records")