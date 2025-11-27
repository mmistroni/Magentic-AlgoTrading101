# Define a tool function
# --- Tools (For Data Retrieval) ---
from pydantic import BaseModel, Field
from typing import List, Dict, Union, Any
import random
import os
import time
import csv
from .models import SignalDataModel
from typing import List, Dict, Any
from google.adk.tools import FunctionTool

def cot_data_tool(market: str) -> Dict[str, Any]:
    """
    TOOL: Simulates retrieving the latest Commitment of Traders (COT) data for a market.
    In a real system, this would make an API call to the CFTC or a data provider.
    """
    print(f"[COT Data Tool] Fetching latest report for {market}...")
    time.sleep(0.5) # Simulate latency
    
    # Simulate a raw net non-commercial position (speculators)
    net_position = random.randint(-150000, 150000)
    
    return {
        "cot_net_position": net_position,
        "date": "2025-11-10"
    }

def cot_search_tool(future_string: str) -> List[Dict[str, Any]]:
    """
    TOOL: Search cftc information for a future.
    """
    return 'vix'



def vix_data_tool() -> Dict[str, Any]:
    """
    TOOL: Simulates retrieving the current VIX (Volatility Index) level.
    In a real system, this would make an API call to a market data provider.
    """
    print("[VIX Data Tool] Fetching current volatility index level...")
    time.sleep(0.3) # Simulate latency
    
    # Simulate VIX level
    vix_level = round(random.uniform(12.0, 35.0), 2)
    
    return {
        "vix_level": vix_level
    }

def feature_engineering_tool(raw_data_uri: str) -> str:
    """Reads the RAW file, adds features, and writes the ENGINEERED file."""
    
    # 1. READ INPUT FILE (URI from Ingestion Agent)
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

    # 3. WRITE OUTPUT FILE (New URI for Signal Agent)
    with open(engineered_path, 'w', newline='') as outfile:
        writer = csv.writer(outfile)
        writer.writerows(engineered_data)
        
    print(f"FEATURE_AGENT Tool executed. ENGINEERED data created at: {engineered_path}")
    return engineered_path

def signal_generation_tool(engineered_data_uri: str) -> SignalDataModel:
    """
    Reads the engineered data file URI, applies mock trading logic,
    and returns the structured SignalDataModel.
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
                return SignalDataModel(signal="Neutral", reason="No engineered data found in file.")
                
            latest_row = data_rows[-1]
            
            # Map the latest features to their names (assuming the header structure from previous mocks)
            latest_features = {
                'COT_Z_Score': float(latest_row[3]),  # Assuming index 3 for Z-Score
                'VIX_Percentile': float(latest_row[4]) # Assuming index 4 for VIX Percentile
            }
            
    except FileNotFoundError:
        return SignalDataModel(signal="Neutral", reason=f"Engineered data file not found at {input_path}.")
    except Exception as e:
        return SignalDataModel(signal="Neutral", reason=f"Error reading/parsing data: {e}.")

    # 2. APPLY TRADING LOGIC
    cot_z = latest_features.get('COT_Z_Score', 0.0)
    vix_p = latest_features.get('VIX_Percentile', 0.0)

    # Logic: Mean-Reversion Strategy
    if cot_z < -1.5 and vix_p > 90.0:
        signal = "Buy"
        reason = f"COT Z-Score ({cot_z}) indicates extreme bearish sentiment, combined with high VIX ({vix_p})."
    elif cot_z > 1.5 and vix_p < 10.0:
        signal = "Sell"
        reason = f"COT Z-Score ({cot_z}) indicates extreme bullish sentiment, combined with low VIX ({vix_p})."
    else:
        signal = "Neutral"
        reason = f"Metrics are within normal bounds. COT Z-Score: {cot_z}, VIX Percentile: {vix_p}."

    # 3. RETURN STRUCTURED OUTPUT (Pydantic Model)
    print(f"SIGNAL_AGENT Tool executed. Signal generated: {signal}")
    return SignalDataModel(signal=signal, reason=reason)


# Assuming DataPointerModel is the type hint for the input parameter,
# though the LlmAgent passes the content of the DataPointerModel's 'uri' field.

# --- MOCK TOOL DEFINITIONS ---

def mock_ingestion_tool() -> str:
    """Creates the RAW data file."""
    file_path = "./temp_data/raw_data_test.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Create RAW data with 3 lines
    raw_data = [
        ['Timestamp', 'Raw_COT_Value', 'Raw_VIX_Value'],
        ['2025-11-20', '10.5', '90.0'],
        ['2025-11-21', '11.2', '85.5'],
        ['2025-11-22', '12.0', '78.0']
    ]
    with open(file_path, 'w', newline='') as f: 
        writer = csv.writer(f)
        writer.writerows(raw_data)
        
    print(f"[INGESTION Agent Tool called. RAW data created at: {file_path}")
    return file_path



def mock_feature_engineering_tool(raw_data_pointer_uri: str) -> str:
    """
    Mocks the Feature Engineering process.
    
    1. Reads the URI from the raw data pointer (simulated).
    2. Writes a new file containing engineered features (simulated).
    3. Returns the URI of the newly created engineered data file.
    
    Args:
        raw_data_pointer_uri: The URI string pointing to the raw data (e.g., './temp_data/raw_data_test.csv').
        
    Returns:
        The URI string pointing to the new engineered data.
    """
    
    # In a real environment, you would use 'raw_data_pointer_uri' 
    # to read data from GCS or a database.
    
    print(f"Mock Tool: Reading raw data from: {raw_data_pointer_uri}")
    
    # 1. Define the output path for the engineered features
    engineered_path = "./temp_data/engineered_data.csv"
    
    # 2. Simulate writing the engineered features
    # This data simulates the computed features (COT Z-Score, VIX percentile, etc.)
    engineered_content = (
        "timestamp,z_score,percentile\n"
        "2025-11-20,-1.7,92.0"
    )
    
    # Ensure the directory exists (handled by your fixture, but good practice)
    os.makedirs(os.path.dirname(engineered_path), exist_ok=True)
    
    with open(engineered_path, 'w') as f: 
        f.write("timestamp,z_score,percentile\n2025-11-20,-1.7,92.0")
    print(f"Mock Tool: Wrote engineered data to: {engineered_path}")
        
    # 3. Return the new URI that the FEATURE_MODEL_GENERATOR will use
    return engineered_path

def mock_signal_generation_tool(feature_data_pointer: str) -> str:
    """Mocks SIGNAL: Reads FEATURE URI, determines signal, and returns the full JSON string."""
    # Since the Signal Agent is a generator, we assume the tool returns the final JSON string.
    # To satisfy the SignalDataModel, the tool returns the data that the LLM will serialize.
    return '{"signal": "Buy", "reason": "Mocked: High COT Z-Score indicates strong bullish conviction."}'



REAL_INGESTION_TOOL = FunctionTool(vix_data_tool)
MOCK_INGESTION_TOOL = FunctionTool(mock_ingestion_tool)
REAL_FEATURE_TOOL = FunctionTool(feature_engineering_tool)
MOCK_FEATURE_TOOL = FunctionTool(mock_feature_engineering_tool)
REAL_SIGNAL_TOOL = FunctionTool(signal_generation_tool)
MOCK_Signal_TOOL = FunctionTool(mock_signal_generation_tool)
