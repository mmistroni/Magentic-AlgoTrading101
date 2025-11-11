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
    tools=[COTDataTool, VIXDataTool]
)
