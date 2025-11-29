from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
# Assuming these imports contain the actual tool logic for the pipeline
from vix_agent.tools import (
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

INGESTION_TOOL_CALLER = LlmAgent(
    name="IngestionToolCaller",
    model='gemini-2.5-flash',
    instruction=f"""
    Use the `vix_data_tool` to fetch the latest data and **return the storage URI as a plain text string**.
    The output string will be automatically saved to the shared context under the key 'ingestion_raw_output'.
    """,
    # 💥 FIX 1: Use the REAL tool FunctionTool wrapper here
    tools=[INGESTION_FT],
    # output_schema is not allowed with tools
)

INGESTION_MODEL_GENERATOR = LlmAgent(
    # ... (Model Generator remains the same) ...
    name="IngestionModelGenerator",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the raw URI string from the shared context key 'ingestion_raw_output'.
    Convert this string into a valid JSON object matching the {DataPointerModel.__name__} schema.
    The URI should be mapped to the 'uri' field.
    **The final JSON output must be returned to be saved as the DataPointerModel.**
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
    Retrieve the **'raw_data_pointer'** from the shared context.
    Call the **`feature_engineering_tool`** using the **URI from the raw_data_pointer** to process the raw data.
    **Return the resulting feature data URI as a plain text string.**
    The output string will be automatically saved to the shared context under the key 'feature_tool_raw_output'.
    """,
    # 💥 FIX 2: Use the REAL tool FunctionTool wrapper here
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
    # 💥 FIX 3: Use the REAL tool FunctionTool wrapper here
    tools=[SIGNAL_FT],
    instruction="""
    You are a data processing assistant. Your current task is to call the `signal_generation_tool`.
    The input for the tool is available in the session state key 'feature_data_pointer'. 
    Pass the URI from that pointer to the tool. 
    Store the tool's raw output (which is a SignalDataModel object) in the session state key 'final_output'.
    """
    # Note: I changed the instruction to save to 'final_output' 
    # to match the final SIGNAL_MODEL_GENERATOR's output_key, simplifying the final step.
)

SIGNAL_MODEL_GENERATOR = LlmAgent(
    # ... (Model Generator remains the same) ...
    name="SignalGenerationAgent",
    description="Generates the final structured trading signal based on the raw signal JSON.",
    model='gemini-2.5-flash',
    output_schema=SignalDataModel, 
    output_key="final_output",     
    tools=[], 
    instruction="""
    Your task is to generate the final output object that strictly adheres to the SignalDataModel.
    The raw data needed for this model is available in the session state key 'final_output' (or 'raw_signal_json' if you revert the CALLER's instruction).
    Use that raw data/JSON to populate the SignalDataModel fields.
    """
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
        SIGNAL_MODEL_GENERATOR
    ]
)