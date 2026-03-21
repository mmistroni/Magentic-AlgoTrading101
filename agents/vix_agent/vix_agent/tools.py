import os
import json
import random
import pandas as pd
from typing import List, Dict, Any
from google.adk.tools import FunctionTool

from .vix_futures_tools import vix_futures_ingestion_tool

def _read_data_from_pandas(input_path: str) -> pd.DataFrame:
    return pd.read_csv(input_path, index_col=0, parse_dates=True)

# ==========================================
# --- BIGQUERY EXTRACTORS (Placeholders) ---
# ==========================================
def fetch_cot_from_bq(market: str) -> pd.DataFrame:
    """Will eventually query BigQuery for COT data."""
    pass 

def fetch_vix_from_bq() -> pd.DataFrame:
    """Will eventually query BigQuery for VIX spot data."""
    pass

# ==========================================
# --- 1. INGESTION TOOLS ---
# ==========================================
def ingestion_tool(market: str) -> str:
    file_path = "./temp_data/raw_data_test.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    raw_data = fetch_cot_from_bq(market)
    raw_data.to_csv(file_path, header=True, index=False)
    
    return file_path

def vix_ingestion_tool() -> str:
    file_path = "./temp_data/vix_raw_data_test.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    raw_data = fetch_vix_from_bq()
    raw_data.to_csv(file_path, header=True, index=False)
    
    return file_path

# ==========================================
# --- 2. MERGE TOOL ---
# ==========================================

def master_data_preparation_tool(market: str, current_date: str) -> str:
    """
    TOOL: Downloads COT, VIX Spot, and VIX Futures, merges them, 
    and returns the URI of the master merged dataset.
    """
    print("Agent called Master Prep Tool. Fetching all data...")
    
    # 1. Fetch all data
    cot_uri = ingestion_tool(market)
    vix_spot_uri = vix_ingestion_tool()
    vix_futures_uri = vix_futures_ingestion_tool(current_date)
    
    # 2. Merge them
    merged_uri = merge_all_features_tool(
        vix_path=vix_spot_uri,
        cot_clean_path=cot_uri,
        vix_futures_path=vix_futures_uri
    )
    
    # 3. Return the single URI to the LLM!
    return merged_uri


def merge_all_features_tool(vix_path: str, cot_clean_path: str, vix_futures_path: str, spx_path: str = "") -> str:
    print("Feature Agent: Starting multi-dataset alignment and merge...")
    merged_path = "./temp_data/master_merged_data.csv"
    os.makedirs(os.path.dirname(merged_path), exist_ok=True)
    
    vix_df = _read_data_from_pandas(vix_path)
    vix_df.index = pd.to_datetime(vix_df.index)
    
    cot_clean_df = _read_data_from_pandas(cot_clean_path)
    cot_clean_df.index = pd.to_datetime(cot_clean_df.index)
    
    futures_df = _read_data_from_pandas(vix_futures_path)
    futures_df.index = pd.to_datetime(futures_df.index)

    start_date = vix_df.index.min()
    end_date = vix_df.index.max()
    daily_index = pd.date_range(start=start_date, end=end_date, freq='D')
    
    cot_daily_filled = cot_clean_df.reindex(daily_index).ffill()
    
    merged_df = vix_df.join(cot_daily_filled, how='left')
    merged_df = merged_df.join(futures_df, how='left')

    if spx_path and os.path.exists(spx_path):
        spx_df = _read_data_from_pandas(spx_path)
        spx_df.index = pd.to_datetime(spx_df.index)
        spx_df = spx_df.add_prefix('spx_') 
        merged_df = merged_df.join(spx_df, how='left')

    merged_df.dropna(subset=[vix_df.columns[0]], inplace=True) 
    merged_df.to_csv(merged_path, header=True)
    print(f"[Merge Tool] Master dataset created with columns: {merged_df.columns.tolist()}")
    
    return merged_path

# ==========================================
# --- 3. FEATURE TOOL ---
# ==========================================
def apply_thresholds_to_features(df: pd.DataFrame, vix_zscore_threshold: float, cot_percentile_threshold: float) -> pd.DataFrame:
    df['Extreme_VIX_Signal'] = (df['VIX_ZScore'] > vix_zscore_threshold).astype(int)
    df['Extreme_COT_Signal'] = (df['COT_Percentile'] < cot_percentile_threshold).astype(int)

    df['Combined_Feature_Signal'] = (
        (df['Extreme_VIX_Signal'] == 1) & 
        (df['Extreme_COT_Signal'] == 1)
    ).astype(int)
    
    df[['Extreme_VIX_Signal', 'Extreme_COT_Signal', 'Combined_Feature_Signal']] = \
        df[['Extreme_VIX_Signal', 'Extreme_COT_Signal', 'Combined_Feature_Signal']].fillna(0)
    
    return df

def calculate_features_tool(merged_data_uri: str, vix_zscore_threshold: float, cot_percentile_threshold: float) -> str:
    print(f'[FEATURES TOOL: VixZ:{vix_zscore_threshold}|CotPcNt:{cot_percentile_threshold}]')
    df = _read_data_from_pandas(merged_data_uri).copy()
    
    df['net_position'] = df['comm_positions_long_all'] - df['comm_positions_short_all']

    window = 252  
    df['VIX_Rolling_Mean'] = df['close'].rolling(window=window).mean()
    df['VIX_Rolling_Std'] = df['close'].rolling(window=window).std()
    df['VIX_ZScore'] = (df['close'] - df['VIX_Rolling_Mean']) / df['VIX_Rolling_Std']

    long_window = 1250 
    df['COT_Rolling_Max'] = df['net_position'].rolling(window=long_window).max()
    df['COT_Rolling_Min'] = df['net_position'].rolling(window=long_window).min()
    df['COT_Percentile'] = (df['net_position'] - df['COT_Rolling_Min']) / \
                        (df['COT_Rolling_Max'] - df['COT_Rolling_Min'])

    if 'vix_front_month_close' in df.columns:
        df['VIX_Basis'] = df['close'] - df['vix_front_month_close']
        df['Backwardation_Signal'] = (df['VIX_Basis'] > 0).astype(int)
    else:
        print("Warning: VIX Futures data missing from merge. Skipping Basis calculation.")

    final_feature_df = apply_thresholds_to_features(
                                 df, 
                                 vix_zscore_threshold=vix_zscore_threshold, 
                                 cot_percentile_threshold=cot_percentile_threshold
                        )
    
    file_path = "./temp_data/master_features.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    final_feature_df.to_csv(file_path, header=True)

    return file_path

# ==========================================
# --- 4. SIGNAL TOOL ---
# ==========================================
def signal_generation_tool(engineered_data_uri: str, market: str) -> str:
    input_path = engineered_data_uri
    signal_path = f"./temp_data/weekly_signal_{market.replace(' ', '_').lower()}.json" 
    os.makedirs(os.path.dirname(signal_path), exist_ok=True)
    
    try:
        df = pd.read_csv(input_path, index_col='date', parse_dates=True)
        df.index = pd.to_datetime(df.index)
        
        target_rows = df.tail(7) 
        print(f'[SIGNAL TOOL] Processing last 7 days:\n{target_rows.index.tolist()}')

        signals_list = []

        for timestamp, row in target_rows.iterrows():
            sig = "Neutral"
            conf = 0.5
            
            vix_z = row.get('VIX_ZScore', 0)
            cot_p = row.get('COT_Percentile', 0.5)
            vix_basis = row.get('VIX_Basis', -1.0) 
            is_backwardation = row.get('Backwardation_Signal', 0)

            if is_backwardation == 1:
                sig = "STRONG BUY VIX / SPIKE DETECTED"
                conf = 0.90
            elif vix_z < -1.5 and cot_p > 0.8:
                sig = "WARNING: VIX Spike Imminent"
                conf = 0.75
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

        with open(signal_path, 'w') as outfile:
            json.dump(signals_list, outfile, indent=2)
        
        return signal_path

    except Exception as e:
        print(f"Error in Weekly Signal Tool: {e}")
        return signal_path

def read_signal_file_tool(uri: str) -> dict:
    try:
        with open(uri, 'r') as f:
            return json.load(f)
    except Exception:
        return {"market": "Error", "signal": "Error", "confidence": 0.0, "justification": "File read failure."}

# ==========================================
# --- ADK WRAPPERS ---
# ==========================================
REAL_INGESTION_TOOL = FunctionTool(ingestion_tool) 
MASTER_PREP_TOOL = FunctionTool(master_data_preparation_tool)
REAL_FEATURE_TOOL = FunctionTool(calculate_features_tool)
REAL_SIGNAL_TOOL = FunctionTool(signal_generation_tool)