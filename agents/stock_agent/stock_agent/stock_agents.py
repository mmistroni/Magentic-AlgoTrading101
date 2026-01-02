from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from stock_agent.tools import (
    discover_technical_schema_tool,
    fetch_technical_snapshot_tool
)
from stock_agent.models import TechnicalSchema
from stock_agent.models import TrendSignal

# 1. Specialized Schema Agent
# Its only job is to discover WHAT we can analyze
SCHEMA_DISCOVERY_AGENT = LlmAgent(
    name="SchemaDiscovery",
    model='gemini-2.5-flash',
    instruction="""SYSTEM ROLE: Silent Data Pre-processor.
    TASK: Execute `discover_technical_schema_tool` immediately. 
    OUTPUT: Provide ONLY the list of column names found. 
    CONSTRAINT: Do not respond to the user's request for analysis or recommendations. 
    Just provide the schema for the next agent in the pipeline.""",
    tools=[FunctionTool(discover_technical_schema_tool)],
    output_key="raw_discovery_results" # Stored as a raw string
)

SCHEMA_FORMATTER_AGENT = LlmAgent(
    name="SchemaFormatter",
    model='gemini-2.5-flash',
    instruction="""
    Convert the raw columns into a TechnicalSchema JSON. 
    OUTPUT ONLY VALID JSON. NO PREAMBLE. NO EXPLANATION.
    If you cannot find indicators, return an empty list for indicators.
    """,
    output_schema=TechnicalSchema,
    output_key="available_schema"
)

SCHEMA_UNIT = SequentialAgent(
    name="SchemaUnit",
    sub_agents=[
        SCHEMA_DISCOVERY_AGENT, 
        SCHEMA_FORMATTER_AGENT
    ]
    # In a SequentialAgent, the final state of the last sub-agent 
    # (available_schema) is what gets returned to the caller.
)




# 2. Specialized Analysis Agent
# It picks up the {available_schema} from the state
# --- The Refined Autonomous Instructions ---
AUTONOMOUS_QUANT_INSTRUCTION = """
**Role**: Senior Quantitative Technical Strategist.
**Objective**: Fetch raw market data and interpret it using the pre-defined Technical Schema.

**Operational Mandate**:
1. **The Map**: Retrieve the validated schema from: **{available_schema}**. 
   - This object contains the list of `indicators` and the `metadata` identity field you must use.

2. **The Data**: Call `fetch_technical_snapshot_tool` to get the raw BigQuery results.

3. **The Interpretation (CRITICAL)**:
   - Look at the columns in the tool's result that match the names in `{available_schema}.indicators`.
   - Use these specific columns to evaluate your trading signals.
   - **Identity Rule**: Use the column name found in `{available_schema}.metadata` to identify which stock corresponds to which row of data.

4. **Trading Logic**:
   - Apply your strategy (Fundamentals + Technicals) to the specific columns identified in Step 3.
   - Issue 'BUY' or 'SELL' only if there is confluence between at least TWO (2) indicators from the schema.
   - Issue 'HOLD' if the identity field is missing or data is inconclusive.

**Constraint**: You must explicitly mention which indicators from the `{available_schema}` led to your final recommendation.
"""

# --- Updated Agent Configuration ---
QUANT_ANALYZER = LlmAgent(
    name="QuantAnalyzer",
    model='gemini-2.5-flash', # Optimized for Dec 2025 multi-step reasoning
    instruction=AUTONOMOUS_QUANT_INSTRUCTION,
    tools=[
        FunctionTool(fetch_technical_snapshot_tool)
        ],
    #output_schema=TrendSignal, # Enforces the Pydantic contract we defined
    output_key='final_trade_signal'
)


# 3. The Unstoppable Pipeline
# We replace the LlmAgent 'TrendStrategist' with a SequentialAgent.
# This FORCES the handoff without needing an orchestrator prompt.
TREND_PIPELINE = SequentialAgent(
    name="TrendStrategist",
    sub_agents=[
        SCHEMA_UNIT,   # Step 1: Discover & Format
        QUANT_ANALYZER # Step 2: Analyze (will now finally be called)
    ]
)