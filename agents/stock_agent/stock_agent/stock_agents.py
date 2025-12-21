from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from stock_agent.tools import (
    discover_technical_schema_tool,
    fetch_today_technical_snapshot_tool
)
from stock_agent.models import TrendSignal

# 1. Specialized Schema Agent
# Its only job is to discover WHAT we can analyze
SCHEMA_AGENT = LlmAgent(
    name="SchemaExplorer",
    model='gemini-3-flash', # Upgraded to the new Dec 2025 standard
    instruction="""
    Call the discover_technical_schema_tool to find all available columns in the BigQuery table.
    Output only the list of technical indicators found.
    """,
    tools=[FunctionTool(discover_technical_schema_tool)],
    output_key="available_schema" # Saved to state for the next agent
)

# 2. Specialized Analysis Agent
# It picks up the {available_schema} from the state
QUANT_ANALYZER = LlmAgent(
    name="QuantAnalyzer",
    model='gemini-3-flash',
    instruction="""
    Using the columns identified in {available_schema}, call fetch_today_technical_snapshot_tool.
    
    Analyze each stock using your expertise in the specific indicators provided.
    Provide a BUY/SELL/HOLD recommendation and a detailed technical justification.
    """,
    tools=[FunctionTool(fetch_today_technical_snapshot_tool)],
    # --- THIS IS WHERE IT FITS ---
    output_schema=TrendSignal, 
    output_key='final_trade_signal'
)

# 3. The Orchestrator
# This ensures step 1 happens before step 2
TREND_PIPELINE = SequentialAgent(
    name="TrendPipeline",
    sub_agents=[SCHEMA_AGENT, QUANT_ANALYZER]
)