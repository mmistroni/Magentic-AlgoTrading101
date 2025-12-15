# Define a tool function
from pydantic import BaseModel, Field
from typing import List, Dict, Union, Any
import random
import os
import time
import csv
from .models import SignalDataModel
from google.adk.tools import FunctionTool
from google.adk.tools import ToolContext 
import os
import csv
from typing import List, Dict, Union, Any
import pandas as pd
import numpy as np
import json

def _get_raw_data(market) -> pd.DataFrame :
    raw_data = [
        ['Timestamp', 'Raw_COT_Value', 'Raw_VIX_Value'],
        ['2025-11-20', '10.5', '90.0'],
    ]

    header = raw_data[0]
    data_rows = raw_data[1:]
    
    # 2. Create the initial DataFrame
    return pd.DataFrame(data_rows, columns=header)

def _get_vix_raw_data() -> pd.DataFrame :
    raw_data = [
        ['date', 'open', 'high', 'low', 'close', 'volume'],
    ['2025-11-20', 16.670000076293945,17.559999465942383,15.239999771118164,15.239999771118164,1000],
    ]
    
    header = raw_data[0]
    data_rows = raw_data[1:]
    
    # 2. Create the initial DataFrame
    return pd.DataFrame(data_rows, columns=header)

def _read_data_from_pandas(input_path:str) -> pd.DataFrame :
    # 1. READ CSV AS DATAFRAME
    # Read the file, treating the first column as the index (Timestamp)
    # Ensure the numerical columns are correctly cast
    return pd.read_csv(
        input_path, 
        )
    
    

def _engineer_features_with_pandas(input_path: str) -> pd.DataFrame:
    """
    Reads data from a CSV as a DataFrame, calculates Z-Scores and Percentiles,
    and saves the engineered DataFrame back to a new CSV.
    
    Args:
        input_path (str): Path to the input CSV (e.g., 'vix_cot_data.csv').
        output_path (str): Path to save the output CSV.
    """
    try:
        # 1. READ CSV AS DATAFRAME
        # Read the file, treating the first column as the index (Timestamp)
        # Ensure the numerical columns are correctly cast
        df = pd.read_csv(
            input_path, 
            index_col='Timestamp', 
            parse_dates=['Timestamp'],
            dtype={'Raw_COT_Value': np.float64, 'Raw_VIX_Value': np.float64}
        )
        print(f"Successfully read input data from {input_path}. Shape: {df.shape}")

        # 2. CALCULATE ACTUAL FEATURES (Core Data Engineering)
        
        # Calculate COT Z-Score: (Value - Mean) / Standard Deviation
        cot_mean = df['Raw_COT_Value'].mean()
        cot_std = df['Raw_COT_Value'].std()
        
        if cot_std == 0:
             df['COT_Z_Score'] = 0.0 # Handle case where all values are the same
        else:
             df['COT_Z_Score'] = (df['Raw_COT_Value'] - cot_mean) / cot_std
        
        # Calculate VIX Percentile Rank (0 to 100)
        # The rank shows the percentage of values in the series less than the current value.
        df['VIX_Percentile'] = df['Raw_VIX_Value'].rank(pct=True) * 100
        print(f'Generating----\n{df}')
        # 3. SAVE ENGINEERED DATAFRAME TO CSV
        return df

    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
        return None
    except Exception as e:
        print(f"An unexpected error occurred during processing: {e}")
        return None

    
def ingestion_tool(market: str) -> str:
    """
    TOOL: Creates the RAW data file at a specific URI and returns the URI string.
    This relies on the LlmAgent's output_key to save the result to state.
    """
    file_path = "./temp_data/raw_data_test.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create RAW data for the pipeline to consume

    raw_data = _get_raw_data(market)

    print(f"[INGESTION Tool] RAW data created is: {raw_data}")
    
    raw_data.to_csv(file_path, header=True)

    print(f"[INGESTION Tool] RAW data created at: {file_path}")
    
    # 💥 CRITICAL FIX: Return the file path string directly.
    return file_path

def vix_ingestion_tool() -> str:
    """
    TOOL: Creates the RAW data file at a specific URI and returns the URI string.
    This relies on the LlmAgent's output_key to save the result to state.
    """
    file_path = "./temp_data/vix_raw_data_test.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create RAW data for the pipeline to consume

    raw_data = _get_vix_raw_data()

    print(f"[INGESTION Tool] VIX RAW data created is: {raw_data}")
    
    raw_data.to_csv(file_path, header=True)

    print(f"[INGESTION Tool] VIX RAW data created at: {file_path}")
    
    # 💥 CRITICAL FIX: Return the file path string directly.
    return file_path

def merge_vix_and_cot_features_tool(vix_path: str, cot_clean_path: str) -> str:
    """
    Merges daily VIX data with weekly COT data using forward-filling to align frequencies.
    
    Args:
        vix_path: Daily VIX DataFrame path, indexed by daily date.
        cot_clean_path: Weekly COT DataFrame path, indexed by weekly (Friday release) date.
        
    Returns:
        A daily DataFrame containing both VIX and the forward-filled COT features.
    """
    print("Feature Agent: Starting VIX/COT frequency alignment and merge...")
    
    # --- Step 1: Align COT to Daily Frequency using Forward Fill (ffill) ---
    file_path = "./temp_data/vix_cot_merged.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create a new index spanning the entire date range of the VIX data
    vix_df = _read_data_from_pandas(vix_path)
    cot_clean_df = _read_data_from_pandas(cot_clean_path)
    start_date = vix_df.index.min()
    end_date = vix_df.index.max()
    daily_index = pd.date_range(start=start_date, end=end_date, freq='D')
    merged_path = "./temp_data/vix_and_cot_merged.csv"

    # Reindex the weekly COT data to this full daily range. 
    # This introduces NaN for all non-reporting days (Sat-Thu).
    cot_daily_filled = cot_clean_df.reindex(daily_index)
    
    # The crucial step: Forward-fill the weekly COT values to every day until the next report.
    cot_daily_filled = cot_daily_filled.ffill()
    
    # --- Step 2: Merge the two datasets ---
    
    # Outer join to ensure we keep all trading days from the VIX data.
    # The index (Date) is shared.
    merged_df = vix_df.merge(
        cot_daily_filled, 
        left_index=True, 
        right_index=True, 
        how='outer'
    )
    
    # Drop rows where VIX data is missing (i.e., weekends/holidays that were in the daily_index)
    # assuming VIX is the authoritative list of trading days.
    # Assuming 'vix_close' is a column in vix_df:
    merged_df.dropna(subset=[vix_df.columns[0]], inplace=True) 
    
    # We now have a daily dataset where COT data changes only once per week (on Friday)
    print(f"Feature Agent: Merge complete. Final daily shape: {merged_df.shape}")
    merged_df.to_csv(merged_path, header=True)
    print(f"[ FEAture - {merged_df.columns}")
    
    return merged_path

    

# The actual Tool Function (This runs on your side)
def calculate_features_tool(
    cot_vix_path: str,  # Assumed to be passed internally
    net_position_column: str, 
    lookback_weeks: List[int]
) -> str:
    """
    Generates the COT Index features for multiple lookback periods.
    """
    print(f'### net position col is:{net_position_column}')

    df = _read_data_from_pandas(cot_vix_path).copy()
    
    print(f'### input df cols are:{df.columns}')
    
    file_path = "./temp_data/vix_cot_features.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)


    for WEEKS in lookback_weeks:
        # (Internal logic is the same efficient pandas code as before)
        COL_INDEX = f'COT_Index_{WEEKS}W'
        
        rolling_stats = df[net_position_column].rolling(window=WEEKS, min_periods=1)
        rolling_min = rolling_stats.min()
        rolling_max = rolling_stats.max()
        
        # Min-Max Normalization (COT Index Formula)
        df[COL_INDEX] = (
            (df[net_position_column] - rolling_min) / 
            (rolling_max - rolling_min)
        ) * 100
        
        # Handle division by zero
        df.loc[rolling_max == rolling_min, COL_INDEX] = 50.0

    df.to_csv(file_path, header=True)

    print(f"[Feature Agent]: new df : {df.head(5)}")
    
    return file_path

def signal_generation_tool(engineered_data_uri: str, market: str) -> str:
    """
    Reads the engineered data file URI, applies trading logic,
    writes the structured SignalDataModel as a **JSON string** to a file,
    and returns the **URI of the signal file**.
    """
    
    input_path = engineered_data_uri
    # Use the market name in the output file path for better organization/debugging
    signal_path = f"./temp_data/signal_output_{market.replace(' ', '_').lower()}.json" 
    os.makedirs(os.path.dirname(signal_path), exist_ok=True)
    latest_features = {}
    
    # --- Helper function to save signal on error ---
    def save_error_signal(signal: str, confidence: float, justification: str) -> str:
        """Saves a default or error signal and returns the path."""
        model_output = SignalDataModel(
            market=market,
            signal=signal,
            confidence=confidence,
            justification=justification
        )
        with open(signal_path, 'w') as f:
            f.write(model_output.model_dump_json(indent=2))
        return signal_path

    # --- 1. READ ENGINEERED DATA ---
    try:
        df = pd.read_csv(input_path, index_col=0, parse_dates=True)
        print(f"[SIGNAL_AGENT Tool] DF from file: {df}")
        # 2. CHECK FOR EMPTY DATA
        if df.empty:
            print(f"[SIGNAL_AGENT Tool] No data in engineered file: {input_path}")
            return save_error_signal("Neutral", 0.0, "No engineered data found in file to generate a signal.")

        # 3. GET LATEST ROW
        # .iloc[-1] always retrieves the last row of the DataFrame
        latest_row = df.iloc[-1]
        
        # 4. EXTRACT REQUIRED FEATURES
        cot_z_score = latest_row['COT_Z_Score']
        vix_percentile = latest_row['VIX_Percentile']
        latest_features = {
            'COT_Z_Score': float(cot_z_score), 
            'VIX_Percentile': float(vix_percentile) 
        }
            
    except FileNotFoundError:
        print(f"[SIGNAL_AGENT Tool] File not found: {input_path}")
        return save_error_signal("Neutral", 0.0, f"Engineered data file not found at {input_path}.")
    except Exception as e:
        print(f"[SIGNAL_AGENT Tool] Error reading data: {e}")
        return save_error_signal("Neutral", 0.0, f"Error reading/parsing data: {e}.")

    # --- 2. APPLY TRADING LOGIC ---
    cot_z = latest_features.get('COT_Z_Score', 0.0)
    vix_p = latest_features.get('VIX_Percentile', 0.0)
    
    # Default values
    signal = "Neutral"
    justification = f"Metrics are within normal bounds. COT Z-Score: {cot_z:.2f}, VIX Percentile: {vix_p:.2f}."
    confidence_score = 0.4 

    # Logic: Mean-Reversion Strategy
    if cot_z < -1.5 and vix_p > 90.0:
        # Extreme short positioning (COT) combined with high volatility (VIX) is typically bullish
        signal = "Buy"
        justification = f"COT Z-Score ({cot_z:.2f}) indicates extreme bearish sentiment, combined with high VIX ({vix_p:.2f}). Strong evidence for a mean-reversion BUY signal."
        confidence_score = 0.85
    elif cot_z > 1.5 and vix_p < 10.0:
        # Extreme long positioning (COT) combined with low volatility (VIX) is typically bearish
        signal = "Sell"
        justification = f"COT Z-Score ({cot_z:.2f}) indicates extreme bullish sentiment, combined with low VIX ({vix_p:.2f}). Strong evidence for a mean-reversion SELL signal."
        confidence_score = 0.75
    
    # --- 3. WRITE STRUCTURED OUTPUT TO FILE ---
    print(f"[SIGNAL_AGENT Tool] Signal generated: {signal}")
    model_output = SignalDataModel(
        market=market, # Now populated from the input argument
        signal=signal, 
        confidence=confidence_score, # Now populated
        justification=justification # Corrected field name
    )
    
    json_generated = model_output.model_dump_json(indent=2)
    print(f"[SIGNAL_AGENT_TOOL] json generated:{json_generated}")
    with open(signal_path, 'w') as outfile:
        # Write the JSON representation of the Pydantic model to the file
        outfile.write(json_generated) 
        
    print(f"[SIGNAL_AGENT Tool] Signal JSON created at: {signal_path}")
    
    # --- 4. RETURN THE URI ---
    return signal_path

def read_signal_file_tool(uri: str) -> dict:
    """Reads the JSON file content and returns it as a dictionary."""
    try:
        with open(uri, 'r') as f:
            return json.load(f)
    except Exception:
        # Handle error case gracefully in the pipeline
        return {"market": "Error", "signal": "Error", "confidence": 0.0, "justification": "File read failure."}



# --------------------------------------------------------------------------
# --- Deprecated/Auxiliary Tools (Kept for completeness but not in pipeline) ---
# --------------------------------------------------------------------------

def cot_data_tool(market: str) -> Dict[str, Any]:
    """AUXILIARY: Simulates retrieving raw COT data (not used in file I/O pipeline)."""
    # ... (original implementation) ...
    return {"cot_net_position": random.randint(-150000, 150000), "date": "2025-11-10"}

def cot_search_tool(future_string: str) -> List[Dict[str, Any]]:
    """AUXILIARY: Search cftc information (not used in pipeline)."""
    return 'vix'

def vix_data_tool() -> Dict[str, Any]:
    """AUXILIARY: Simulates retrieving VIX level (not used in file I/O pipeline)."""
    # ... (original implementation) ...
    return {"vix_level": round(random.uniform(12.0, 35.0), 2)}

# --------------------------------------------------------------------------
# --- FunctionTool Wrappers (Used by vix_agents.py) ---
# --------------------------------------------------------------------------
# These are kept separate to clearly show which tools are used by the agents.
# We are only using the real tools now.



REAL_INGESTION_TOOL = FunctionTool(ingestion_tool) # Updated to use the new ingestion_tool
REAL_FEATURE_TOOL = FunctionTool(calculate_features_tool)
REAL_SIGNAL_TOOL = FunctionTool(signal_generation_tool)