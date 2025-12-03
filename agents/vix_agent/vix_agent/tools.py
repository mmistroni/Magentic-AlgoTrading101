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
from google.adk.tools import ToolContext 
import os
import csv
from typing import List, Dict, Union, Any

def ingestion_tool(market: str) -> str:
    """
    TOOL: Creates the RAW data file at a specific URI and returns the URI string.
    This relies on the LlmAgent's output_key to save the result to state.
    """
    file_path = "./temp_data/raw_data_test.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create RAW data for the pipeline to consume
    raw_data = [
        ['Timestamp', 'Raw_COT_Value', 'Raw_VIX_Value'],
        ['2025-11-20', '10.5', '90.0'],
        ['2025-11-21', '11.2', '85.5'],
        ['2025-11-22', '12.0', '78.0']
    ]
    with open(file_path, 'w', newline='') as f: 
        writer = csv.writer(f)
        writer.writerows(raw_data)
        
    print(f"[INGESTION Tool] RAW data created at: {file_path}")
    
    # 💥 CRITICAL FIX: Return the file path string directly.
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
        raise Exception(f"Error: Input file not found at {input_path}")

    # 3. WRITE OUTPUT FILE
    with open(engineered_path, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(engineered_data)
        
    print(f"[FEATURE_AGENT Tool] ENGINEERED data created at: {engineered_path}")
    return engineered_path

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
        with open(input_path, 'r', newline='') as infile:
            reader = csv.reader(infile)
            header = next(reader)
            
            # Read the last row (latest data point)
            data_rows = list(reader)
            if not data_rows:
                print(f"[SIGNAL_AGENT Tool] No data in engineered file: {input_path}")
                return save_error_signal("Neutral", 0.0, "No engineered data found in file to generate a signal.")
                
            latest_row = data_rows[-1]
            print(f"[SIGNAL AGENT]Latest Row:{latest_row}")
            # Map the latest features (assuming header structure: [0]TS, [1]COT, [2]VIX, [3]COT_Z, [4]VIX_P)
            latest_features = {
                'COT_Z_Score': float(latest_row[3]), 
                'VIX_Percentile': float(latest_row[4]) 
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