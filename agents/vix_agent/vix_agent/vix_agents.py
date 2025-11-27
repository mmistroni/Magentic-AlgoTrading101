from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from vix_agent.tools import cot_data_tool, vix_data_tool, mock_ingestion_tool,\
                            mock_feature_engineering_tool, \
                            mock_signal_generation_tool
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
    tools=[
        #mock_ingestion_tool
        ],
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
    tools=[
        #mock_feature_engineering_tool
        ], 
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

# Rename the old SIGNAL_AGENT to reflect its new role

SIGNAL_TOOL_CALLER = LlmAgent(
    name="SignalToolCallerAgent",
    description="Calls the signal generation tool with the feature data URI and saves the raw signal output.",
    tools=[], # <-- FIX: Must be an empty list for Dependency Injection
    # No output_schema is set here to satisfy the framework's rule
    # The agent will use its prompt to guide it to call the tool and save the output.
    instruction="""
    You are a data processing assistant. Your current task is to call the `mock_signal_generation_tool`.
    The input for the tool is available in the session state key 'feature_data_pointer'. 
    Pass the URI from that pointer to the tool. 
    Store the tool's raw string output in the session state key 'raw_signal_json'.
    """
)

SIGNAL_MODEL_GENERATOR = LlmAgent(
    name="SignalGenerationAgent",
    description="Generates the final structured trading signal based on the raw signal JSON.",
    output_schema=SignalDataModel, 
    output_key="final_output",     
    tools=[], 
    instruction="""
    Your task is to generate the final output object that strictly adheres to the SignalDataModel.
    The raw data needed for this model is available in the session state key 'raw_signal_json'.
    Use that raw JSON string to populate the SignalDataModel fields.
    """
)