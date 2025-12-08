from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
# Assuming these imports contain the actual tool logic for the pipeline
from vix_agent.tools import (
    ingestion_tool,
    vix_ingestion_tool, 
    feature_engineering_tool, 
    signal_generation_tool,
    read_signal_file_tool
)
from vix_agent.models import SignalDataModel, DataPointerModel 
# Note: RawDataModel and FeatureDataModel are not used in the simplified flow.

# --- FunctionTool Wrappers (No Change) ---
# Using ingestion_tool for the primary ingestion call
INGESTION_FT = FunctionTool(ingestion_tool)
VIX_INGESTION_FT = FunctionTool(vix_ingestion_tool) 
FEATURE_FT = FunctionTool(feature_engineering_tool)
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


# ---

## 🛠️ STAGE 2: FEATURE ENGINEERING (UPDATED to read raw URI)

FEATURE_TOOL_CALLER = LlmAgent(
    name="FeatureToolCaller",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the **COT URI string** from the shared context key **'ingestion_raw_output'**.
    Retrieve the **VIX URI string** from the shared context key **'vix_raw_output_uri'**.
    
    Call the **`feature_engineering_tool`** passing:
    1. The COT URI string to the **`raw_data_uri`** argument.
    2. The VIX URI string to a new argument, perhaps **`vix_data_uri`**.
    
    **CRITICAL: YOUR FINAL OUTPUT MUST BE ONLY THE RAW URI STRING RETURNED BY THE TOOL** (which should now be the URI of the combined, engineered data).
    """,
    tools=[FEATURE_FT], 
    output_key='feature_tool_raw_output' # Saves the engineered URI string
)

NEW_FEATURE_TOOL_CALLER = LlmAgent(
    name="FeatureToolCaller",
    model='gemini-2.5-flash',
    instruction=f"""
    **Task 1: Analyze and Define Extremity (The 'Smarter' Part)**
    
    1.  Retrieve the COT URI string from **'ingestion_raw_output'** and the VIX URI string from **'vix_raw_output_uri'**.
    2.  **Hypothesize** the required features for predicting a 'huge drop in VIX prices' (i.e., resolution of extreme fear). These must include measures of:
        * **VIX Extremity:** A quantitative measure of how far VIX is from its recent historical average (e.g., a Z-score threshold).
        * **COT Extremity:** A quantitative measure of extreme speculative positioning (Non-Commercial Net Position) relative to its historical range (e.g., a percentile threshold).
    3.  **Define the Specific Thresholds:** Based on general market knowledge (e.g., Z-score > 2.0, Percentile < 10%), determine the explicit numerical criteria for a 'hot' point.

    **Task 2: Instruct the Tool Call**
    
    Call the **`feature_engineering_tool`** passing the two URIs AND the **explicit, numerically defined thresholds** needed to calculate the 'Extreme VIX' and 'Extreme COT' binary signals.
    
    The tool must return **ONLY** the URI string of the file containing the final engineered features.
    """,
    tools=[FEATURE_FT], 
    output_key='feature_tool_raw_output'
)


# ***REMOVED***: FEATURE_MODEL_GENERATOR

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
        FEATURE_TOOL_CALLER,            
        # 4. Signal Generation, Reading, and Model Validation (Rest of the flow remains the same)
        SIGNAL_TOOL_CALLER,             # 3. Uses engineered URI, gets signal file URI
        SIGNAL_READER_AGENT,            # 4. Uses signal file URI, gets signal JSON dict
        SIGNAL_MODEL_GENERATOR          # 5. Uses signal JSON dict, validates Pydantic model
    ]
)

# You should now use COT_WORKFLOW_PIPELINE_SIMPLIFIED in your tests!