from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
# Assuming these imports contain the actual tool logic for the pipeline
from vix_agent.tools import (
    ingestion_tool,
    vix_ingestion_tool, 
    merge_vix_and_cot_features_tool,
    calculate_features_tool, 
    signal_generation_tool,
    read_signal_file_tool
)
from vix_agent.models import SignalDataModel, DataPointerModel, WeeklySignalReport
# Note: RawDataModel and FeatureDataModel are not used in the simplified flow.

# --- FunctionTool Wrappers (No Change) ---
# Using ingestion_tool for the primary ingestion call
INGESTION_FT = FunctionTool(ingestion_tool)
VIX_INGESTION_FT = FunctionTool(vix_ingestion_tool) 
MERGE_INGESTION_FT = FunctionTool(merge_vix_and_cot_features_tool) 

FEATURE_FT = FunctionTool(calculate_features_tool)
SIGNAL_FT = FunctionTool(signal_generation_tool)
READER_FT = FunctionTool(read_signal_file_tool)


## 🚀 STAGE 1: DATA INGESTION (Simplified)
# The output is now a raw URI string, not a Pydantic dict.

INGESTION_TOOL_CALLER = LlmAgent(
    name="IngestionToolCaller",
    model='gemini-2.5-flash',
    instruction=f"""
    Use the `ingestion_tool` to fetch the latest data for the requested market. The tool returns the storage URI string.
    **CRITICAL:** Your final text output must be **ONLY** the URI string returned by the tool.
    """,
    tools=[INGESTION_FT], 
    output_key='ingestion_raw_output' # Saves the raw URI string
)

VIX_INGESTION_TOOL_CALLER = LlmAgent(
    name="VIXIngestionAgent",
    model='gemini-2.5-flash',
    instruction=f"""
    Use the **`vix_ingestion_tool`** to fetch the latest VIX price data. The tool returns the storage URI string.
    **CRITICAL:** Your final text output must be **ONLY** the URI string returned by the tool.
    """,
    tools=[VIX_INGESTION_FT], 
    output_key='vix_raw_output_uri' # Saves the raw VIX URI string
)

MERGE_ALIGNMENT_TOOL_CALLER = LlmAgent(
    name="DataAlignmentAgent", # Renamed for clarity: Focus on ALIGNMENT/MERGING
    model='gemini-2.5-flash',
    instruction=f"""
    **CRITICAL TASK:** Your job is to merge two time-series datasets: 
    1. The daily **Clean VIX Data** located at: **{{vix_raw_output_uri}}**
    2. The weekly **Clean COT Data** located at: **{{ingestion_raw_output}}**
    
    Use the **`merge_vix_and_cot_features`** tool. You must pass both input URIs and define a new output URI (e.g., 'vix_cot_merged.csv').
    
    **CRITICAL:** Your final text output must be **ONLY** the URI string returned by the tool 
    (the path to the newly created merged data file).
    """,
    # This assumes the LLM Agent is executed with the URIs passed as context variables.
    tools=[MERGE_INGESTION_FT], 
    output_key='vix_cot_merged_output_uri' # Remains the correct output key
)


# ---

## 🛠️ STAGE 2: FEATURE ENGINEERING (UPDATED to read raw URI)
NEW_FEATURE_TOOL_CALLER = LlmAgent(
    name="FeatureToolCaller",
    model='gemini-2.5-flash',
    instruction=f"""
    **CRITICAL TASK: CALCULATE ALL REQUIRED FEATURES**

    1. The necessary VIX and COT data is merged and aligned in the file located at: **{{vix_cot_merged_output_uri}}**.
    2. **Hypothesize** and **Define** the explicit numerical thresholds for VIX Z-score and COT Percentile needed to predict a 'huge drop in VIX prices'.
    3. Call the **`calculate_features_tool`** passing the **merged URI** AND the **explicit, numerically defined thresholds**.
    
    **STRICT FORMAT REQUIREMENT:** Your final text output must be **ONLY** the raw URI string returned by the tool. 
    **DO NOT** add any introductory phrases, explanations, or context around the URI.
    """,
    tools=[FEATURE_FT], 
    output_key='feature_tool_raw_output'
)


# ---

## 🚦 STAGE 3: SIGNAL GENERATION (UPDATED to read raw URI)

SIGNAL_TOOL_CALLER = LlmAgent(
    name="SignalToolCallerAgent",
    model='gemini-2.5-flash',
    description="Calls the signal generation tool with the feature data URI and saves the raw signal output.",
    tools=[SIGNAL_FT],
    instruction="""
    Retrieve the engineered data URI string from the shared context key **'feature_tool_raw_output'**.
    Retrieve the market name from the shared context key **'market'**.
    Call the `signal_generation_tool` using the extracted URI and market name.
    
    **CRITICAL: YOUR FINAL OUTPUT MUST BE ONLY THE RAW URI STRING RETURNED BY THE TOOL.**
    """,
    output_key='signal_file_uri_raw' # Key used to save the raw signal URI string
)

# ---

## 🚦 STAGE 3: SIGNAL GENERATION (UPDATED to pick LAST ROW)

## 🚦 STAGE 3: SIGNAL GENERATION (Updated for 7-Day Lookback)
SIGNAL_TOOL_CALLER = LlmAgent(
    name="SignalToolCallerAgent",
    model='gemini-2.5-flash',
    description="Calls the tool to generate a signal report for the last 7 trading days.",
    tools=[SIGNAL_FT],
    instruction="""
    1. Retrieve the engineered data URI from **'feature_tool_raw_output'**.
    2. Retrieve the market name from **'market'**.
    
    **CRITICAL:** Instruct the `signal_generation_tool` to process the **LAST 7 ROWS** of the data. 
    This provides a weekly view of the VIX Z-score and COT Percentile trends.
    
    Your final output must be **ONLY** the raw URI string for the generated signal file.
    """,
    output_key='signal_file_uri_raw' 
)

# ---

## ✅ FINAL STEP: FILE READING AND BATCH VALIDATION
SIGNAL_READER_AGENT = LlmAgent(
    name="SignalReaderAgent",
    model='gemini-2.5-flash',
    instruction="""
    Retrieve the raw URI string from **'signal_file_uri_raw'**. 
    Use the **`read_signal_file_tool`** to extract the data.
    
    **CRITICAL:** The output will be a JSON LIST of 7 objects. Return the raw JSON list content.
    """,
    tools=[READER_FT],
    output_key='signal_json_content_raw'
)

SIGNAL_MODEL_GENERATOR = LlmAgent(
    name="SignalModelGenerator",
    model='gemini-2.5-flash',
    instruction=f"""
    1. You will receive a JSON list containing 7 days of data.
    2. Map this list to the 'signals' field in the **{WeeklySignalReport.__name__}**.
    3. Evaluate the 7-day trend: identify if the COT positioning is becoming more extreme or mean-reverting.
    4. Provide a final 'weekly_trend' summary.
    """,
    tools=[], 
    output_schema=WeeklySignalReport, # Using the WRAPPER here
    output_key='final_signal_json' 
)


# ---

## 🎯 THE UPDATED PIPELINE DEFINITION

COT_WORKFLOW_PIPELINE = SequentialAgent(
    name="COTTradingSignalPipeline_V3",
    sub_agents=[
        INGESTION_TOOL_CALLER,          
        VIX_INGESTION_TOOL_CALLER,            
        MERGE_ALIGNMENT_TOOL_CALLER,     
        NEW_FEATURE_TOOL_CALLER,
        SIGNAL_TOOL_CALLER,       # Added back with 'last row' logic
        SIGNAL_READER_AGENT,      # Added back
        SIGNAL_MODEL_GENERATOR    # Final Pydantic validation
    ]
)
# You should now use COT_WORKFLOW_PIPELINE_SIMPLIFIED in your tests!