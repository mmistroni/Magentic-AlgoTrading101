from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
# Assuming these imports contain the actual tool logic for the pipeline
from vix_agent.tools import (
    ingestion_tool,
    vix_data_tool, # Used for Ingestion (if COT data is not used)
    feature_engineering_tool, 
    signal_generation_tool
)
from vix_agent.models import RawDataModel, FeatureDataModel, SignalDataModel, DataPointerModel

# --- Utility: Wrap Real Tools (Use the core logic, not the mocks) ---
INGESTION_FT = FunctionTool(vix_data_tool) # Using vix_data_tool as a stand-in for ingestion
FEATURE_FT = FunctionTool(feature_engineering_tool)
SIGNAL_FT = FunctionTool(signal_generation_tool)

# --- STAGE 1: DATA INGESTION ---
# --- STAGE 1: DATA INGESTION ---

# 1. INGESTION_TOOL_CALLER
# Instruction focuses on calling the tool, which now handles state saving internally 
# to a separate key ('ingestion_file_uri') via ToolContext. The output_key is removed 
# as the tool's return value (an acknowledgement) is now irrelevant.

INGESTION_FT = FunctionTool(ingestion_tool) 
# Assuming DataPointerModel is imported:
# from vix_agent.models import DataPointerModel 

# --- STAGE 1: DATA INGESTION ---

### 1. The Tool Caller Agent (LlmAgent)

# This agent calls the tool and relies on its 'output_key' to save the URI.
INGESTION_TOOL_CALLER = LlmAgent(
    name="IngestionToolCaller",
    model='gemini-2.5-flash',
    instruction=f"""
    Use the `ingestion_tool` to fetch the latest data for the requested market. The tool returns the storage URI string.
    **CRITICAL:** Your final text output must be **ONLY** the URI string returned by the tool.
    This string will be saved automatically to the shared context using the output key.
    """,
    # Pass the FunctionTool wrapper
    tools=[INGESTION_FT], 
    # 💥 FIX: The tool's return value (the URI) is captured and saved to this key.
    output_key='ingestion_raw_output' 
)

### 2. The Model Generator Agent (LlmAgent)

# This agent reads the URI from the key set by the first agent and wraps it in Pydantic JSON.
INGESTION_MODEL_GENERATOR = LlmAgent(
    name="IngestionModelGenerator",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the raw URI string from the shared context key **'ingestion_raw_output'**. 
    Convert this string into a valid JSON object matching the DataPointerModel schema.
    The URI should be mapped to the 'uri' field.
    The final JSON output must be returned to be saved as the DataPointerModel under 
    the key 'raw_data_pointer'.
    """,
    tools=[], 
    output_schema=DataPointerModel,
    output_key='raw_data_pointer'
)


# --- STAGE 2: FEATURE ENGINEERING ---

FEATURE_TOOL_CALLER = LlmAgent(
    name="FeatureToolCaller",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the JSON content from the shared context key **'raw_data_pointer'**.
    
    Extract the **'uri'** field from that JSON object. 
    Call the **`feature_engineering_tool`** passing ONLY the extracted URI string to the `raw_data_uri` argument.
    
    **CRITICAL: YOUR FINAL OUTPUT MUST BE ONLY THE RAW URI STRING RETURNED BY THE TOOL. DO NOT ADD ANY DESCRIPTIVE TEXT, PREFIXES, OR ADDITIONAL PHRASES.**
    """,
    tools=[FEATURE_FT], 
    output_key='feature_tool_raw_output'
)

FEATURE_MODEL_GENERATOR = LlmAgent(
    # ... (Model Generator remains the same) ...
    name="FeatureModelGenerator",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the raw URI string from the shared context key **'feature_tool_raw_output'** (this is the engineered data URI).
    Convert this URI string into a valid JSON object matching the {DataPointerModel.__name__} schema.
    The URI should be mapped to the 'uri' field.
    The final JSON output must be returned and will be saved to the key 'feature_data_pointer'.
    """,
    tools=[],
    output_schema=DataPointerModel,
    output_key='feature_data_pointer'
)

# --- STAGE 3: SIGNAL GENERATION ---

SIGNAL_TOOL_CALLER = LlmAgent(
    name="SignalToolCallerAgent",
    model='gemini-2.5-flash',
    description="Calls the signal generation tool with the feature data URI and saves the raw signal output.",
    tools=[SIGNAL_FT],
    instruction="""
    Retrieve the JSON content of the **'feature_data_pointer'** from the shared context. 
    
    Extract the 'uri' and 'market' fields from this JSON. 
    Call the `signal_generation_tool` using the extracted URI and market name.
    
    **CRITICAL: YOUR FINAL OUTPUT MUST BE ONLY THE RAW URI STRING RETURNED BY THE TOOL. DO NOT ADD ANY DESCRIPTIVE TEXT, PREFIXES, OR JSON WRAPPERS LIKE {"tool_response": ...}. JUST RETURN THE STRING.**
    """,
    output_key='signal_file_uri_raw' # Key used to save the raw string
)

SIGNAL_MODEL_GENERATOR = LlmAgent(
    name="SignalModelGenerator",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the raw URI string from the shared context key **'signal_file_uri_raw'**. 
    
    **CRITICAL:** The URI points to a JSON file containing the final trading signal. You must instruct the environment to **read the content of this JSON file**.
    
    Then, take the content of that file and use it to construct a new JSON object that strictly adheres to the **{SignalDataModel.__name__}** schema.
    The final JSON output (representing the signal itself) must be returned.
    """,
    tools=[], 
    output_schema=SignalDataModel, # The desired final output type
    output_key='final_signal_json' # The key holding the actual Signal JSON
)

# --- THE PIPELINE ---
COT_WORKFLOW_PIPELINE = SequentialAgent(
    name="COTTradingSignalPipeline",
    sub_agents=[
        INGESTION_TOOL_CALLER,
        INGESTION_MODEL_GENERATOR,
        FEATURE_TOOL_CALLER,
        FEATURE_MODEL_GENERATOR,
        SIGNAL_TOOL_CALLER,
        #SIGNAL_MODEL_GENERATOR
    ]
)
