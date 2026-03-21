import os
import json
import pandas as pd
import pytest

# Import your tools (Adjust the import path based on your folder structure)
from vix_agent.tools import (
    ingestion_tool,
    vix_ingestion_tool,
    vix_futures_ingestion_tool,
    merge_all_features_tool,
    calculate_features_tool,
    signal_generation_tool
)
from vix_agent.vix_futures_tools import vix_futures_ingestion_tool


# --- 1. DEFINE YOUR MOCK BEHAVIORS ---
def mock_bq_cot_data(market: str) -> pd.DataFrame:
    return pd.DataFrame([
        ['2025-11-20', 150000, 100000],
        ['2025-11-21', 155000, 102000]
    ], columns=['Timestamp', 'comm_positions_long_all', 'comm_positions_short_all'])

def mock_bq_vix_data() -> pd.DataFrame:
    return pd.DataFrame([
        ['2025-11-20', 16.67, 17.55, 15.23, 15.23, 1000],
        ['2025-11-21', 15.23, 16.00, 14.50, 14.80, 1200]
    ], columns=['date', 'open', 'high', 'low', 'close', 'volume'])

def mock_bq_vix_futures_data(target_date: str) -> pd.DataFrame:
    return pd.DataFrame([
        ['2025-11-20', 16.10],
        ['2025-11-21', 15.50]
    ], columns=['date', 'vix_front_month_close'])


# --- 2. THE TEST USING MONKEYPATCH ---
# Notice we just pass 'monkeypatch' as an argument. Pytest handles injecting it automatically.
def test_end_to_end_tool_pipeline(monkeypatch):
    
    # 3. OVERRIDE THE FUNCTIONS
    # Format: monkeypatch.setattr("path.to.module.function_name", replacement_function)
    monkeypatch.setattr("vix_agent.tools.fetch_cot_from_bq", mock_bq_cot_data)
    monkeypatch.setattr("vix_agent.tools.fetch_vix_from_bq", mock_bq_vix_data)
    monkeypatch.setattr("vix_agent.vix_futures_tools.fetch_vix_futures_from_bq", mock_bq_vix_futures_data)
    
    print("\n--- Starting Pipeline Test ---")
         

    # 4. ACT: Call the tools! 
    # Because of monkeypatch.setattr(), these will naturally hit your mock functions above.
    cot_raw_uri = ingestion_tool("VIX")
    vix_spot_raw_uri = vix_ingestion_tool()
    vix_futures_raw_uri = vix_futures_ingestion_tool("2024-01-15")     
    
    # ==========================================
    # 1. ARRANGE & ACT: INGESTION STAGE
    # ==========================================
    # Call the ingestion tools (These generate the raw CSVs)
    cot_raw_uri = ingestion_tool("VIX")
    vix_spot_raw_uri = vix_ingestion_tool()
    
    # We will pass a specific date to the futures tool
    # (Assuming you added the vix_futures_ingestion_tool from earlier)
    vix_futures_raw_uri = vix_futures_ingestion_tool("2024-01-15")
    
    assert os.path.exists(cot_raw_uri), "COT raw file missing"
    assert os.path.exists(vix_spot_raw_uri), "VIX spot raw file missing"
    assert os.path.exists(vix_futures_raw_uri), "VIX futures raw file missing"

    # ==========================================
    # 2. ACT: MERGE STAGE
    # ==========================================
    # Pass the URIs generated above into the merge tool
    merged_uri = merge_all_features_tool(
        vix_path=vix_spot_raw_uri,
        cot_clean_path=cot_raw_uri,
        vix_futures_path=vix_futures_raw_uri
    )
    
    assert os.path.exists(merged_uri), "Merged file was not created"
    
    # Quick check that the merge tool actually combined the columns
    df_merged = pd.read_csv(merged_uri)
    assert 'comm_positions_long_all' in df_merged.columns, "Merge dropped COT data"

    assert 'vix_front_month_close' in df_merged.columns, "Merge dropped Futures data"

    # ==========================================
    # 3. ACT: FEATURE ENGINEERING STAGE
    # ==========================================
    # Pass the merged URI and some LLM-hypothesized thresholds
    features_uri = calculate_features_tool(
        merged_data_uri=merged_uri,
        vix_zscore_threshold=2.0,
        cot_percentile_threshold=0.10
    )
    
    assert os.path.exists(features_uri), "Feature file was not created"
    
    # Verify the math happened
    df_features = pd.read_csv(features_uri)
    assert 'VIX_ZScore' in df_features.columns, "Z-Score column missing"
    assert 'VIX_Basis' in df_features.columns, "VIX Basis column missing"

    # ==========================================
    # 4. ACT: SIGNAL GENERATION STAGE
    # ==========================================
    # Finally, generate the weekly JSON report
    signal_json_uri = signal_generation_tool(
        engineered_data_uri=features_uri,
        market="VIX"
    )
    
    assert os.path.exists(signal_json_uri), "Final JSON signal file was not created"

    # ==========================================
    # 5. ASSERT: FINAL VERIFICATION
    # ==========================================
    with open(signal_json_uri, 'r') as f:
        signals = json.load(f)
        
    assert isinstance(signals, list), "Output should be a JSON list"
    assert len(signals) > 0, "Signal list is empty"
    
    # Check the schema of the first daily signal
    first_signal = signals[0]
    assert "date" in first_signal
    assert "signal" in first_signal
    assert "confidence" in first_signal
    assert "justification" in first_signal
    
    print("\n✅ PIPELINE TEST PASSED! The final signal output looks like this:")
    print(json.dumps(first_signal, indent=2))