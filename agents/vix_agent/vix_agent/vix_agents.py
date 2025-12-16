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
from vix_agent.models import SignalDataModel, DataPointerModel 
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

## ✅ FINAL STEP: FILE READING AND MODEL VALIDATION (New/Updated Agents)

SIGNAL_READER_AGENT = LlmAgent(
    name="SignalReaderAgent",
    model='gemini-2.5-flash',
    instruction="""
    Retrieve the raw URI string from the shared context key **'signal_file_uri_raw'**. 
    Use the **`read_signal_file_tool`** to read the JSON file content at that URI.
    
    **CRITICAL:** Your final output must be **ONLY** the JSON dictionary returned by the tool.
    """,
    tools=[READER_FT],
    output_key='signal_json_content_raw' # New key to hold the actual signal DICT content
)

SIGNAL_MODEL_GENERATOR = LlmAgent(
    name="SignalModelGenerator",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the final signal JSON dictionary directly from the shared context key **'signal_json_content_raw'**.
    The content is already a valid JSON dictionary from the file. **Do not modify it or add analysis.**
    Convert this dictionary into a new JSON object that strictly adheres to the **{SignalDataModel.__name__}** schema.
    """,
    tools=[], 
    output_schema=SignalDataModel, 
    output_key='final_signal_json' # The key holding the final validated Signal JSON
)

# ---

## 🎯 THE SIMPLIFIED PIPELINE DEFINITION

COT_WORKFLOW_PIPELINE = SequentialAgent(
    name="COTTradingSignalPipeline_Simplified",
    sub_agents=[
        INGESTION_TOOL_CALLER,          # 1. Gets raw URI
        # 2. VIX Data Ingestion (NEW AGENT)
        VIX_INGESTION_TOOL_CALLER,            # Output: 'vix_raw_output_uri' (VIX URI) 
        # 3. FEATURE ENGINEERING (MUST BE UPDATED TO USE BOTH URIs)
        MERGE_ALIGNMENT_TOOL_CALLER,     
        NEW_FEATURE_TOOL_CALLER       
        # 4. Signal Generation, Reading, and Model Validation (Rest of the flow remains the same)
        #SIGNAL_TOOL_CALLER,             # 3. Uses engineered URI, gets signal file URI
        #SIGNAL_READER_AGENT,            # 4. Uses signal file URI, gets signal JSON dict
        #SIGNAL_MODEL_GENERATOR          # 5. Uses signal JSON dict, validates Pydantic model
    ]
)

# You should now use COT_WORKFLOW_PIPELINE_SIMPLIFIED in your tests!