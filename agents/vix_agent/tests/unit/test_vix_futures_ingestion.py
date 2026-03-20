import os
import pandas as pd
import pytest

# IMPORT YOUR EXISTING TOOL HERE
# Adjust 'vix_agent.tools' if your file is named something else
from vix_agent.vix_futures_tools import vix_futures_ingestion_tool

def test_vix_futures_ingestion_tool_integration():
    """
    Integration test to ensure the existing vix_futures_ingestion_tool 
    fetches data, saves it correctly, and prevents forward-looking bias.
    """
    # 1. Arrange
    test_date = "2023-10-15"
    expected_path = "./temp_data/vix_futures_raw_test.csv"
    target_dt = pd.to_datetime(test_date)
    
    # Clean up any old test files before running to ensure a fresh test
    if os.path.exists(expected_path):
        os.remove(expected_path)
        
    # 2. Act
    output_uri = vix_futures_ingestion_tool(test_date)
    
    # 3. Assert - File Creation
    assert output_uri == expected_path, f"Expected URI {expected_path}, got {output_uri}"
    assert os.path.exists(output_uri), "The tool did not create the CSV file."
    
    # 4. Assert - Data Format
    df = pd.read_csv(output_uri, index_col='date', parse_dates=True)
    assert not df.empty, "The resulting DataFrame is empty."
    assert 'vix_front_month_close' in df.columns, "The DataFrame is missing the required column."
    assert df.index.name == 'date', "The index name should be 'date'."
    
    # 5. Assert - NO Forward-Looking Bias (Critical for backtesting)
    max_date_in_df = df.index.max()
    assert max_date_in_df <= target_dt, f"Data leakage! Found data on {max_date_in_df}, which is after target {target_dt}"
    
    # 6. Assert - Valid Data
    assert df['vix_front_month_close'].notna().any(), "All prices in the output are NaN."

    print(f"\n[SUCCESS] Test passed! Data properly sliced up to {max_date_in_df.date()}")