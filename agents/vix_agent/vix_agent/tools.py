# Define a tool function
from pydantic import BaseModel, Field
from typing import List, Dict, Union, Any
import random
import os
import time
import csv
from .models import SignalDataModel
from typing import List, Dict, Any
from google.adk.tools import FunctionTool

# --------------------------------------------------------------------------
# --- Core Pipeline Tool Definitions (Used by LlmAgents) ---
# --------------------------------------------------------------------------

def ingestion_tool(market: str) -> str:
    """
    TOOL: Creates the RAW data file at a specific URI.
    The LlmAgent expects this function to return the URI string for the next stage.
    """
    file_path = "./temp_data/raw_data_test.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create RAW data for the pipeline to consume
    raw_data = [
        ['Timestamp', 'Raw_COT_Value', 'Raw_VIX_Value'],
        ['2025-11-20', '10.5', '90.0'],
        ['2025-11-21', '11.2', '85.5'],
        ['2025-11-22', '12.0', '78.0'] # Last row is used for feature calculation
    ]
    with open(file_path, 'w', newline='') as f: 
        writer = csv.writer(f)
        writer.writerows(raw_data)
        
    print(f"[INGESTION Tool] RAW data created at: {file_path}")
    return file_path


def feature_engineering_tool(raw_data_uri: str) -> str:
    """
    Reads the RAW file, adds features, and writes the ENGINEERED file.
    Returns the URI of the engineered file.
    """
    
    input_path = raw_data_uri
    engineered_path = "./temp_data/engineered_data.csv"
    engineered_data = []
    
    try:
        with open(input_path, 'r', newline='') as infile:
            reader = csv.reader(infile)
            header = next(reader)
            
            # Write new header with calculated features
            engineered_data.append(header + ['COT_Z_Score', 'VIX_Percentile'])
            
            # 2. ADD FEW LINES / CALCULATE FEATURES (Mock Logic)
            for row_num, row in enumerate(reader, start=1):
                # Mock calculation: Z-Score = 0.5 + (row_num * 0.1)
                z_score = 0.5 + (row_num * 0.1)
                # Mock calculation: Percentile = 95 - (row_num * 5)
                percentile = 95 - (row_num * 5)
                
                engineered_data.append(row + [f"{z_score:.2f}", f"{percentile:.2f}"])
                
    except FileNotFoundError:
        print(f"Error: Input file not found at {input_path}")
        return ""

    # 3. WRITE OUTPUT FILE
    with open(engineered_path, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(engineered_data)
        
    print(f"[FEATURE_AGENT Tool] ENGINEERED data created at: {engineered_path}")
    return engineered_path


def signal_generation_tool(engineered_data_uri: str) -> str:
    """
    Reads the engineered data file URI, applies trading logic,
    and returns the structured SignalDataModel as a **JSON string**.
    """
    
    input_path = engineered_data_uri
    latest_features = {}
    
    try:
        # 1. READ ENGINEERED DATA
        with open(input_path, 'r', newline='') as infile:
            reader = csv.reader(infile)
            header = next(reader)
            
            # Read the last row (latest data point)
            data_rows = list(reader)
            if not data_rows:
                # Returns a default model as JSON string
                model_output = SignalDataModel(signal="Neutral", reason="No engineered data found in file.")
                return model_output.model_dump_json()
                
            latest_row = data_rows[-1]
            
            # Map the latest features to their names (assuming header structure)
            latest_features = {
                'COT_Z_Score': float(latest_row[3]), 
                'VIX_Percentile': float(latest_row[4]) 
            }
            
    except FileNotFoundError:
        model_output = SignalDataModel(signal="Neutral", reason=f"Engineered data file not found at {input_path}.")
        return model_output.model_dump_json()
    except Exception as e:
        model_output = SignalDataModel(signal="Neutral", reason=f"Error reading/parsing data: {e}.")
        return model_output.model_dump_json()

    # 2. APPLY TRADING LOGIC
    cot_z = latest_features.get('COT_Z_Score', 0.0)
    vix_p = latest_features.get('VIX_Percentile', 0.0)

    # Logic: Mean-Reversion Strategy (Note: This matches the expected "Neutral" in the test)
    if cot_z < -1.5 and vix_p > 90.0:
        signal = "Buy"
        reason = f"COT Z-Score ({cot_z:.2f}) indicates extreme bearish sentiment, combined with high VIX ({vix_p:.2f})."
    elif cot_z > 1.5 and vix_p < 10.0:
        signal = "Sell"
        reason = f"COT Z-Score ({cot_z:.2f}) indicates extreme bullish sentiment, combined with low VIX ({vix_p:.2f})."
    else:
        signal = "Neutral"
        reason = f"Metrics are within normal bounds. COT Z-Score: {cot_z:.2f}, VIX Percentile: {vix_p:.2f}."

    # 3. RETURN STRUCTURED OUTPUT AS JSON STRING
    print(f"[SIGNAL_AGENT Tool] Signal generated: {signal}")
    model_output = SignalDataModel(signal=signal, reason=reason)
    return model_output.model_dump_json() # 💥 CRITICAL: Return JSON string for LLM

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
REAL_FEATURE_TOOL = FunctionTool(feature_engineering_tool)
REAL_SIGNAL_TOOL = FunctionTool(signal_generation_tool)