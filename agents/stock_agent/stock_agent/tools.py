import os
from dataclasses import dataclass
from google.cloud import bigquery
import logging
from datetime import date, timedelta

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

    logging.info(f'====TAbleREf={table_ref}|')
    table = client.get_table(table_ref)
    logging.info('===============Now getting ll fields')

    # We return a simple dict or string for the agent to parse
    return {field.name: field.field_type for field in table.schema}

def fetch_technical_snapshot_tool(target_date: str = "today"):
    """
    Queries BigQuery for technical data for a specific day.
    Args:
        target_date: The date to query. Can be 'today', 'yesterday', or a date string 'YYYY-MM-DD'.
    """
    client = bigquery.Client()
    dataset_id = 'gcp_shareloader'
    table_id = 'finviz-premarket'
    table_ref = f"{client.project}.{dataset_id}.{table_id}"
    
    print(f'Query tool: querying for {target_date}')


    # Handle relative date logic
    query_date = date.today()
    if target_date.lower() == "yesterday":
        query_date = date.today() - timedelta(days=1)
    elif target_date.lower() != "today":
        # Attempt to parse specific date if provided
        query_date = target_date 

    query = f"""
        SELECT * FROM `{table_ref}`
        WHERE cob = @query_date
    """
    
    # Using query parameters for security and cleaner syntax
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("query_date", "DATE", query_date)
        ]
    )
    
    query_job = client.query(query, job_config=job_config)
    df = query_job.to_dataframe()
    
    if df.empty:
        return f"No data found for {query_date}."
    
    return df.to_json(orient="records")