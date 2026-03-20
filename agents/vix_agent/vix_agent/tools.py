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
    
    

def ingestion_tool(market: str) -> str:
    """
    TOOL: Creates the RAW data file at a specific URI and returns the URI string.
    This relies on the LlmAgent's output_key to save the result to state.
    """
    file_path = "./temp_data/raw_data_test.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create RAW data for the pipeline to consume

    raw_data = _get_raw_data(market)

    raw_data.to_csv(file_path, header=True)

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

    raw_data.to_csv(file_path, header=True)

    # 💥 CRITICAL FIX: Return the file path string directly.
    return file_path

def merge_all_features_tool(vix_path: str, cot_clean_path: str, vix_futures_path: str, spx_path: str = "") -> str:
    """
    Merges Daily VIX Spot, Weekly COT, Daily VIX Futures, and optionally SPX.
    Uses forward-filling for COT to align weekly data to daily trading days.
    """
    print("Feature Agent: Starting multi-dataset alignment and merge...")
    merged_path = "./temp_data/master_merged_data.csv"
    os.makedirs(os.path.dirname(merged_path), exist_ok=True)
    
    # 1. Load the core datasets and ensure their indexes are explicitly datetime
    vix_df = _read_data_from_pandas(vix_path)
    vix_df.index = pd.to_datetime(vix_df.index)
    
    cot_clean_df = _read_data_from_pandas(cot_clean_path)
    cot_clean_df.index = pd.to_datetime(cot_clean_df.index)
    
    futures_df = _read_data_from_pandas(vix_futures_path)
    futures_df.index = pd.to_datetime(futures_df.index)

    # 2. Align COT to Daily Frequency using Forward Fill
    start_date = vix_df.index.min()
    end_date = vix_df.index.max()
    daily_index = pd.date_range(start=start_date, end=end_date, freq='D')
    
    cot_daily_filled = cot_clean_df.reindex(daily_index).ffill()
    
    # 3. Join everything to the VIX Spot index (Left Join keeps only trading days)
    merged_df = vix_df.join(cot_daily_filled, how='left')
    merged_df = merged_df.join(futures_df, how='left')

    # 4. Integrate SPX if the path is provided
    if spx_path and os.path.exists(spx_path):
        spx_df = _read_data_from_pandas(spx_path)
        spx_df.index = pd.to_datetime(spx_df.index)
        # Rename SPX columns so they don't clash with VIX 'close'/'open'
        spx_df = spx_df.add_prefix('spx_') 
        merged_df = merged_df.join(spx_df, how='left')

    # Drop any remaining rows where VIX Spot data is missing
    merged_df.dropna(subset=[vix_df.columns[0]], inplace=True) 
    
    merged_df.to_csv(merged_path, header=True)
    print(f"[Merge Tool] Master dataset created with columns: {merged_df.columns.tolist()}")
    
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
    Z-score, COT Percentile, and the new VIX Term Structure Basis.
    """
    print(f'[FEATURES TOOL: VixZ:{vix_zscore_threshold}|CotPcNt:{cot_percentile_threshold}]')
    df = _read_data_from_pandas(merged_data_uri).copy()
    
    # 2. Calculate net position
    df['net_position'] = df['comm_positions_long_all'] - df['comm_positions_short_all']

    # 3. Calculate VIX Z-Score (1-year window)
    window = 252  
    df['VIX_Rolling_Mean'] = df['close'].rolling(window=window).mean()
    df['VIX_Rolling_Std'] = df['close'].rolling(window=window).std()
    df['VIX_ZScore'] = (df['close'] - df['VIX_Rolling_Mean']) / df['VIX_Rolling_Std']

    # 4. Calculate COT Percentile Rank (5-year window)
    long_window = 1250 
    df['COT_Rolling_Max'] = df['net_position'].rolling(window=long_window).max()
    df['COT_Rolling_Min'] = df['net_position'].rolling(window=long_window).min()
    df['COT_Percentile'] = (df['net_position'] - df['COT_Rolling_Min']) / \
                        (df['COT_Rolling_Max'] - df['COT_Rolling_Min'])

    # 4.5 🚀 NEW: Calculate VIX Term Structure Basis (Spot vs Futures)
    # Basis = VIX Spot - VIX Front Month Future
    if 'vix_front_month_close' in df.columns:
        df['VIX_Basis'] = df['close'] - df['vix_front_month_close']
        
        # When Basis > 0, the market is in BACKWARDATION (Panic mode / Spike happening)
        df['Backwardation_Signal'] = (df['VIX_Basis'] > 0).astype(int)
    else:
        print("Warning: VIX Futures data missing from merge. Skipping Basis calculation.")

    # 5. Apply thresholds to create binary signals
    final_feature_df = apply_thresholds_to_features(
                                 df, 
                                 vix_zscore_threshold=vix_zscore_threshold, 
                                 cot_percentile_threshold=cot_percentile_threshold
                        )
    
    file_path = "./temp_data/master_features.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    final_feature_df.to_csv(file_path, header=True)

    return file_path



def signal_generation_tool(engineered_data_uri: str, market: str) -> str:
    """
    Processes the last 7 trading days of data to provide a weekly context 
    and generates signals for each day, incorporating VIX Term Structure.
    """
    input_path = engineered_data_uri
    signal_path = f"./temp_data/weekly_signal_{market.replace(' ', '_').lower()}.json" 
    os.makedirs(os.path.dirname(signal_path), exist_ok=True)
    
    try:
        df = pd.read_csv(input_path, index_col='date', parse_dates=True)
        df.index = pd.to_datetime(df.index)
        
        # Ensure we don't crash if there are fewer than 7 rows
        target_rows = df.tail(7) # CHANGED to tail(7) to get the MOST RECENT days
    
        print(f'[SIGNAL TOOL] Processing last 7 days:\n{target_rows.index.tolist()}')

        signals_list = []

        for timestamp, row in target_rows.iterrows():
            sig = "Neutral"
            conf = 0.5
            
            # 1. Extract existing features
            vix_z = row.get('VIX_ZScore', 0)
            cot_p = row.get('COT_Percentile', 0.5)
            
            # 2. Extract new Futures features (Default to -1 / Contango if missing)
            vix_basis = row.get('VIX_Basis', -1.0) 
            is_backwardation = row.get('Backwardation_Signal', 0)

            # --- SIGNAL LOGIC ---
            
            # Condition A: Active Panic (Backwardation)
            # Spot VIX is higher than Futures. The market is actively crashing / VIX is spiking.
            if is_backwardation == 1:
                sig = "STRONG BUY VIX / SPIKE DETECTED"
                conf = 0.90
            
            # Condition B: The "Spring is Coiled" (Complacency Setup)
            # VIX is abnormally low (Z < -1.5), but Commercials are heavily long VIX/short SPX
            elif vix_z < -1.5 and cot_p > 0.8:
                sig = "WARNING: VIX Spike Imminent"
                conf = 0.75
                
            # Condition C: Volatility Crush (Mean Reversion)
            # VIX is extremely high, but Futures are much lower, predicting a return to normal
            elif vix_z > 2.5 and is_backwardation == 0:
                sig = "SELL VIX / Volatility Crush Expected"
                conf = 0.80

            signals_list.append({
                "date": str(timestamp.date()),
                "market": market,
                "signal": sig,
                "confidence": conf,
                "justification": f"VIX Z: {vix_z:.2f} | COT %: {cot_p:.2f} | VIX Basis: {vix_basis:.2f} (Back: {is_backwardation})"
            })

        print(f'[SIGNAL TOOL] Generated {len(signals_list)} daily signals.')

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