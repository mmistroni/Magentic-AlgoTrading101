# test_tools.py (Rewritten)

import pytest
from pytest_mock import MockerFixture
from typing import List
import os

# NOTE: The imports are now correct based on your structure
from stock_strategy_agent import tools
from stock_strategy_agent.models import GetSchemaInput, GetSchemaOutput, FieldInfo 

# --- Mock Data Definitions (Unchanged) ---
class MockSchemaField:
    def __init__(self, name: str, field_type: str):
        self.name = name
        self.field_type = field_type

MOCK_BIGQUERY_SCHEMA: List[MockSchemaField] = [
    MockSchemaField(name="symbol", field_type="STRING"),
    MockSchemaField(name="timestamp", field_type="TIMESTAMP"),
    MockSchemaField(name="close_price", field_type="FLOAT"),
    MockSchemaField(name="volume", field_type="INT64"),
]

# --- Test Case 1: Successful Schema Retrieval ---
def test_get_bigquery_schema_for_table_success(mocker: MockerFixture):
    """
    Tests successful retrieval and simplification, verifying the full table ID 
    is correctly constructed from the environment and input table name.
    """
    
    # 1. Mock Environment Variables (Critical for the new tool logic)
    TEST_PROJECT = "stock_strategy" # Your desired project ID
    TEST_DATASET = "market_data"
    
    # Patch os.environ to set the variables required by tools.py
    mocker.patch.dict(os.environ, {'PROJECT_ID': TEST_PROJECT, 'BQ_DATASET': TEST_DATASET})
    
    # The input now only contains the table name
    test_table_name = "ohlcv_candles"
    test_input = GetSchemaInput(table_id=test_table_name)
    
    # The full ID that the tool should construct and call BQ with
    expected_full_id = f"{TEST_PROJECT}.{TEST_DATASET}.{test_table_name}"

    # --- Setup the Mock BigQuery Client Chain ---

    mock_client = mocker.MagicMock()
    mock_table = mocker.MagicMock()
    mock_table.schema = MOCK_BIGQUERY_SCHEMA
    mock_client.get_table.return_value = mock_table
    
    # 2. Patch the 'get_bq_client' function (now correctly scoped to 'stock_strategy_agent.tools')
    mocker.patch(
        'stock_strategy_agent.tools.get_bq_client', 
        return_value=mock_client
    )

    # --- Execute the Function ---
    result = tools.get_bigquery_schema_for_table(test_input)

    # --- Assertions ---
    
    # 1. VERIFY: The mock client was called with the FULL reconstructed table ID
    mock_client.get_table.assert_called_once_with(expected_full_id)
    
    # 2. VERIFY: The final output is correctly simplified
    expected_output = GetSchemaOutput(
        fields=[
            FieldInfo(field_name="symbol", bigquery_type="STRING"),
            FieldInfo(field_name="timestamp", bigquery_type="TIMESTAMP"),
            FieldInfo(field_name="close_price", bigquery_type="FLOAT"),
            FieldInfo(field_name="volume", bigquery_type="INT64"),
        ]
    )
    assert result == expected_output
    assert len(result.fields) == 4

# --- Test Case 2: Exception Handling ---
def test_get_bigquery_schema_for_table_exception_handling(mocker: MockerFixture):
    """Tests that the function returns an empty list gracefully on error."""
    
    # Set necessary environment variables for the function to run past the initial check
    mocker.patch.dict(os.environ, {'PROJECT_ID': 'stock_strategy', 'BQ_DATASET': 'market_data'})

    # 1. Create a mock client and configure it to raise an exception
    mock_client = mocker.MagicMock()
    mock_client.get_table.side_effect = Exception("Simulated BQ Permission Error")
    
    # 2. Patch get_bq_client to return this error-raising client
    mocker.patch(
        'stock_strategy_agent.tools.get_bq_client', 
        return_value=mock_client
    )
    
    # --- Execute and Assert ---
    test_input = GetSchemaInput(table_id="bad_table")
    result = tools.get_bigquery_schema_for_table(test_input)
    
    # Assert that the function returned the expected empty list of fields
    assert result.fields == []
    
    # Assert that the function attempted to get the table
    mock_client.get_table.assert_called_once()