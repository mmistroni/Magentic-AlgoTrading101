from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from vix_agent.tools import cot_data_tool, vix_data_tool, mock_ingestion_tool
from vix_agent.models import RawDataModel, FeatureDataModel, SignalDataModel, DataPointerModel
from vix_agent.tools import cot_data_tool, vix_data_tool

INGESTION_AGENT = LlmAgent(
    name="DataIngestionAgent",
    model='gemini-2.5-flash',
    instruction=f"""
    Use the COTDataTool and VIXDataTool to fetch the latest data.
    After fetching, **write the data to persistent storage (e.g., a file or GCS bucket)**.
    Create a {DataPointerModel.__name__} object with the resulting storage URI.
    **Save the {DataPointerModel.__name__} object to the shared Context** under the key 'raw_data_pointer'.
    """,
    tools=[mock_ingestion_tool]
)

FEATURE_AGENT = LlmAgent(
    name="FeatureEngineeringAgent",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the 'raw_data_pointer' ({DataPointerModel.__name__}) from the shared Context.
    Use the URI to **read the raw data**, calculate the necessary features (COT Z-Score, VIX percentile, etc.).
    **Write the resulting feature data to new storage location** (e.g., a file or GCS bucket).
    Create a new {DataPointerModel.__name__} object with this new URI.
    **Save the new {DataPointerModel.__name__} object to the shared Context** under the key 'feature_data_pointer'.
    """,
    tools=[] # Still requires no external tools, only computation
)

SIGNAL_AGENT = LlmAgent(
    name="SignalGenerationAgent",
    model='gemini-2.5-flash',
    instruction=f"""
    Retrieve the 'feature_data_pointer' ({DataPointerModel.__name__}) from the shared Context.
    Use the URI to **read the engineered features**.
    Analyze the features to determine a final 'Buy', 'Sell', or 'Neutral' signal, structured as a **SignalDataModel**.
    **Return the final SignalDataModel as the output**. (No new pointer is needed.)
    """,
    tools=[]
)