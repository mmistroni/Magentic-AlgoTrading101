from typing import List, Dict, Any
from google.cloud import bigquery
from .models import FieldInfo, GetSchemaInput,  GetSchemaOutput
from google.cloud import bigquery
import os

# ----------------------------------------------
# 2. The Tool Function
# ----------------------------------------------
# 1. Define a global variable to hold the client instance.
_BQ_CLIENT_INSTANCE = None
try:
    # Read the required project and dataset IDs
    PROJECT_ID = os.environ['PROJECT_ID']
    BQ_DATASET = os.environ['BQ_DATASET']
except KeyError as e:
    # This will prevent the client from initializing if variables are missing
    print(f"FATAL ERROR: Environment variable {e} not set. Cannot initialize live BigQuery tool.")
    PROJECT_ID = None
    BQ_DATASET = None



def get_bq_client():
    """Returns the single, initialized BigQuery client instance."""
    global _BQ_CLIENT_INSTANCE
    
    # Check if the client has already been created
    if _BQ_CLIENT_INSTANCE is None:
        print("--- Initializing BigQuery Client for the first time... ---")
        try:
            # 2. Initialization logic is performed only if None
            _BQ_CLIENT_INSTANCE = bigquery.Client() 
        except Exception as e:
            print(f"ERROR: Failed to initialize BQ client. Check credentials. {e}")
            # Depending on need, you might raise the error or return a mock client
            raise e
            
    return _BQ_CLIENT_INSTANCE

def get_bigquery_schema_for_table(input: GetSchemaInput) -> GetSchemaOutput:
    """
    TOOL: Reconstructs the full table ID from environment variables and the input table name, 
    fetches the schema, and returns a clean list of field names and their BigQuery types.
    """
    
    # ⚠️ New logic to construct the full table ID
    if not PROJECT_ID or not BQ_DATASET:
        # Fallback for mocking/missing env vars
        print("MOCK RUN: Missing BQ environment variables. Returning sample schema.")
        return GetSchemaOutput(fields=[
            FieldInfo(field_name="symbol", bigquery_type="STRING"),
            FieldInfo(field_name="close_price", bigquery_type="FLOAT"),
        ])
        
    # Construct the full BigQuery table ID
    full_table_id = f"{PROJECT_ID}.{BQ_DATASET}.{input.table_name}"
    
    client = get_bq_client()  
    print(f"\n--- Fetching live schema for table: {full_table_id} ---")
    
    try:
        # 1. Use the full_table_id to fetch the table reference
        table_ref = client.get_table(full_table_id)
        raw_schema = table_ref.schema
        
        # 2. Process and simplify the output
        simple_fields: List[FieldInfo] = []
        for field in raw_schema:
            simple_fields.append(FieldInfo(
                field_name=field.name,
                bigquery_type=field.field_type
            ))
            
        print(f"--- Tool Success: Returned {len(simple_fields)} fields. ---")
        return GetSchemaOutput(fields=simple_fields)

    except Exception as e:
        print(f"--- Tool Error: Failed to fetch schema for {full_table_id}. Error: {e} ---")
        return GetSchemaOutput(fields=[])