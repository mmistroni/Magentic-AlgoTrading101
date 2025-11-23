from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from vix_agent.tools import cot_data_tool, vix_data_tool, mock_ingestion_tool,\
                            mock_feature_engineering_tool
from vix_agent.models import RawDataModel, FeatureDataModel, SignalDataModel, DataPointerModel
from vix_agent.tools import cot_data_tool, vix_data_tool

# --- STAGE 1: DATA INGESTION ---

INGESTION_TOOL_CALLER = LlmAgent(
    name="IngestionToolCaller",
    model='gemini-2.5-flash',
    instruction=f"""
    Use the `mock_ingestion_tool` to fetch the latest data and **return the storage URI as a plain text string**.
    The output string will be automatically saved to the shared context under the key 'ingestion_raw_output'.
    """,
    tools=[mock_ingestion_tool],
    # output_schema=DataPointerModel # <-- REMOVED: Cannot have tools + schema
)

INGESTION_MODEL_GENERATOR = LlmAgent(
    name="IngestionModelGenerator",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the raw URI string from the shared context key 'ingestion_raw_output'.
    Convert this string into a valid JSON object matching the {DataPointerModel.__name__} schema.
    The URI should be mapped to the 'uri' field.
    **The final JSON output must be returned to be saved as the DataPointerModel.**
    """,
    tools=[], # <-- CORRECT: No tools allowed with output_schema
    output_schema=DataPointerModel,
    output_key='raw_data_pointer' # <-- CRUCIAL: Saves the Pydantic object under the correct key
)

# --- STAGE 2: FEATURE ENGINEERING ---

FEATURE_TOOL_CALLER = LlmAgent(
    name="FeatureToolCaller",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the **'raw_data_pointer'** from the shared context.
    Call the **`mock_feature_engineering_tool`** using the **URI from the raw_data_pointer** to process the raw data.
    **Return the resulting feature data URI as a plain text string.**
    The output string will be automatically saved to the shared context under the key 'feature_tool_raw_output'.
    """,
    # FIX 1: MUST include the tool in the tools list for it to be callable
    tools=[mock_feature_engineering_tool], 
    output_key='feature_tool_raw_output' # This key holds the URI string
)

FEATURE_MODEL_GENERATOR = LlmAgent(
    name="FeatureModelGenerator",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the raw URI string from the shared context key **'feature_tool_raw_output'** (this is the engineered data URI).
    Convert this URI string into a valid JSON object matching the {DataPointerModel.__name__} schema.
    The URI should be mapped to the 'uri' field.
    **The final JSON output must be returned and will be saved to the key 'feature_data_pointer'.**
    """,
    tools=[],
    output_schema=DataPointerModel,
    output_key='feature_data_pointer' # CRUCIAL: Saves the Pydantic object under the correct key
)
# --- STAGE 3: SIGNAL GENERATION (This agent was already correct) ---

SIGNAL_AGENT = LlmAgent(
    name="SignalGenerationAgent",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the 'feature_data_pointer' from the shared Context.
    Use this pointer to determine a final 'Buy', 'Sell', or 'Neutral' signal.
    **Return the final SignalDataModel as the output.**
    """,
    # NOTE: If this agent calls a tool (like a mock signal generation tool), you must 
    # split it into a CALLER and GENERATOR pair, similar to the above.
    # We will assume for now it only generates the schema based on context.
    tools=[],
    output_schema=SignalDataModel,
    output_key='final_output' # <-- CRUCIAL: Saves the final result
)

# --- THE FINAL PIPELINE DEFINITION (You must use this in your Run