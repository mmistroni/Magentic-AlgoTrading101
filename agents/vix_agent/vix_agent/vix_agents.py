from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent
from vix_agent.tools import cot_data_tool, vix_data_tool
from vix_agent.models import RawDataModel, FeatureDataModel, SignalDataModel
from vix_agent.tools import cot_data_tool, vix_data_tool

INGESTION_AGENT = LlmAgent(
    name="DataIngestionAgent",
    model='gemini-2.5-flash',
    instruction="""
    Use the COTDataTool and VIXDataTool to fetch the latest data for the target market.
    After retrieval, structure the combined raw data into the RawDataModel Pydantic object
    and **save it directly to the shared Context** under the key 'raw_market_data'.
    """,
    tools=[cot_data_tool, vix_data_tool]
)

FEATURE_AGENT = LlmAgent(
    name="FeatureEngineeringAgent",
    model='gemini-2.5-flash',
    instruction="""
    Retrieve the 'raw_market_data' from the shared Context.
    Calculate the COT Z-Score (based on historical context) and VIX percentile.
    Generate the FeatureDataModel and **save it to the shared Context** under the key 'engineered_features'.
    """,
    tools=[] # No external tools needed, only computation
)

SIGNAL_AGENT = LlmAgent(
    name="SignalGenerationAgent",
    model='gemini-2.5-flash',
    instruction="""
    Retrieve the 'engineered_features' from the shared Context.
    Analyze the Z-Score and VIX percentile to determine a 'Buy', 'Sell', or 'Neutral' signal.
    Generate the final SignalDataModel and **return it as the final output**.
    """,
    tools=[]
)

