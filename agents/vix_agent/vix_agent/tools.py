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


def apply_thresholds_to_features(df: pd.DataFrame, vix_zscore_threshold: float, cot_percentile_threshold: float) -> pd.DataFrame:
    """
    Applies the LLM-defined thresholds to VIX Z-Score and COT Percentile 
    to create binary signal columns (1/0).
    """
    
    # --- 1. Apply VIX Extremity Threshold ---
    # Extreme VIX is defined by a Z-Score HIGHER than the threshold (e.g., Z > 2.5)
    
    # We use a numpy/pandas where/condition approach for speed
    df['Extreme_VIX_Signal'] = (df['VIX_ZScore'] > vix_zscore_threshold).astype(int)
    
    # --- 2. Apply COT Extremity Threshold ---
    # Extreme COT is defined by a Percentile LOWER than the threshold (e.g., P < 0.10, or 10%)
    # This means Commercial traders are extremely net-short (a contrarian sign of market bottoms)
    
    df['Extreme_COT_Signal'] = (df['COT_Percentile'] < cot_percentile_threshold).astype(int)

    # --- 3. (Optional) Create a Combined Feature ---
    # While the Signal Agent will handle the final logic, it's often useful 
    # to combine the feature in the feature engineering step.
    
    # The combined signal is 1 only when BOTH conditions are met (the contrarian setup)
    df['Combined_Feature_Signal'] = (
        (df['Extreme_VIX_Signal'] == 1) & 
        (df['Extreme_COT_Signal'] == 1)
    ).astype(int)
    
    # Fill NaN values (e.g., from rolling window startup) with 0 for safety
    df[['Extreme_VIX_Signal', 'Extreme_COT_Signal', 'Combined_Feature_Signal']] = \
        df[['Extreme_VIX_Signal', 'Extreme_COT_Signal', 'Combined_Feature_Signal']].fillna(0)
    
    return df


# The actual Tool Function (This runs on your side)
def calculate_features_tool(
    merged_data_uri: str,
    vix_zscore_threshold: float,
    cot_percentile_threshold: float) -> str:
    """
    Performs all feature engineering, including Net Position calculation, 
    Z-score/Percentile calculation, and applying the LLM-defined thresholds.
    Returns the URI of the final feature file.
    """
    # 1. Load data from merged_data_uri:
    print(f'[FEATURES TOOL: VixZ:{vix_zscore_threshold}|CotPcNt:{cot_percentile_threshold}]')
    df = _read_data_from_pandas(merged_data_uri).copy()
    
    # 2. calculate net position
    # Assuming 'df' is your loaded merged DataFrame
    df['net_position'] = df['comm_positions_long_all'] - df['comm_positions_short_all']

    # 3. Calculate VIX Z-Score (using a lookback window)
    # Define a window (e.g., 252 trading days = approx. 1 year)
    window = 252  

    # Calculate Rolling Mean and Standard Deviation
    df['VIX_Rolling_Mean'] = df['close'].rolling(window=window).mean()
    df['VIX_Rolling_Std'] = df['close'].rolling(window=window).std()

    # Calculate the Z-Score
    df['VIX_ZScore'] = (df['close'] - df['VIX_Rolling_Mean']) / df['VIX_Rolling_Std']

    # 4. Calculate COT Percentile Rank (using a lookback window)
    # Define a long window (e.g., 1250 trading days = approx. 5 years)
    long_window = 1250 

    # Calculate Rolling Max and Min for the Net Position
    df['COT_Rolling_Max'] = df['net_position'].rolling(window=long_window).max()
    df['COT_Rolling_Min'] = df['net_position'].rolling(window=long_window).min()

    # Calculate the COT Oscillator (Percentile Rank)
    df['COT_Percentile'] = (df['net_position'] - df['COT_Rolling_Min']) / \
                        (df['COT_Rolling_Max'] - df['COT_Rolling_Min'])
    # 5. Apply thresholds to create binary signals:
    #    Extreme_VIX_Signal = 1 if VIX_ZScore > vix_zscore_threshold
    #    Extreme_COT_Signal = 1 if COT_Percentile < cot_percentile_threshold
    # --- Example of function call inside calculate_features_tool ---
    final_feature_df = apply_thresholds_to_features(
                                 df, 
                                 vix_zscore_threshold=vix_zscore_threshold, 
                                 cot_percentile_threshold=cot_percentile_threshold
                        )

    
    # 6. Save the final DataFrame and return the new URI string
    print(f'[Feature Tool] Final col input df cols are:{final_feature_df.columns}')
    
    print(f'[Feature Tool] Cot Th:{cot_percentile_threshold} - Vix Z:{vix_zscore_threshold}')
    
    
    file_path = "./temp_data/vix_cot_features.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)


    final_feature_df.to_csv(file_path, header=True)

    print(f'[FEATURE TOOL]. OUtput file:{file_path}')
    
    print(f'[FEATURE TOOL]. :{final_feature_df.head(3)}')
    
    return file_path


def signal_generation_tool(engineered_data_uri: str, market: str) -> str:
    """
    Processes the last 7 trading days of data to provide a weekly context 
    and generates signals for each day.
    """
    input_path = engineered_data_uri
    signal_path = f"./temp_data/weekly_signal_{market.replace(' ', '_').lower()}.json" 
    os.makedirs(os.path.dirname(signal_path), exist_ok=True)
    
    try:
        df = pd.read_csv(input_path, index_col=0, parse_dates=True)
        df.index = pd.to_datetime(df.index)
        
        print(f'SignalTool[Head ]\n{df.head(7)}')
        print('----------------------------')
        print(f'SignalTool[Tail ]\n{df.tail(7)}')
        

        # Ensure we don't crash if there are fewer than 7 rows
        target_rows = df.head(7)
    
        print(f'[SiGNal Tool]\n{target_rows}')


        signals_list = []

        for timestamp, row in target_rows.iterrows():
            # Logic remains similar but applied per day
            sig = "Neutral"
            conf = 0.5
            
            # Using the calculated features from your calculate_features_tool
            vix_z = row.get('VIX_ZScore', 0)
            cot_p = row.get('COT_Percentile', 0.5)

            # Bearish Setup for Short Selling (VIX Low/Falling, COT High)
            if vix_z < -1.5 and cot_p > 0.8:
                sig = "Sell/Short"
                conf = 0.75
            
            signals_list.append({
                "date": str(timestamp.date()),
                "market": market,
                "signal": sig,
                "confidence": conf,
                "justification": f"VIX Z: {vix_z:.2f} | COT %: {cot_p:.2f}"
            })

        print(f'[SIGNAL TOOL] signal json:\n{signals_list}')

        # Save as a JSON list
        with open(signal_path, 'w') as outfile:
            json.dump(signals_list, outfile, indent=2)
        
        return signal_path

    except Exception as e:
        print(f"Error in Weekly Signal Tool: {e}")
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