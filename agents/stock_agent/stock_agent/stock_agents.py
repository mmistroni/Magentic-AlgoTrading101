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
    instruction="Call `discover_technical_schema_tool` and list every column name found. Just list them clearly.",
    tools=[FunctionTool(discover_technical_schema_tool)],
    output_key="raw_discovery_results" # Stored as a raw string
)

SCHEMA_FORMATTER_AGENT = LlmAgent(
    name="SchemaFormatter",
    model='gemini-2.5-flash',
    instruction="""
    1. Retrieve the raw column names from the context key: **{raw_discovery_results}**.
    2. Map these literal strings into the TechnicalSchema.
    3. DO NOT look at the user's trading request. Focus ONLY on the data in {raw_discovery_results}.
    """,
    output_schema=TechnicalSchema,
    output_key="available_schema" # This key is now the 'Source of Truth'
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


# 3. The Orchestrator
# This ensures step 1 happens before step 2
TREND_PIPELINE = LlmAgent(
    name="TrendStrategist",
    model='gemini-2.5-flash',
    instruction="""
    You are the Lead Investment Strategist. Your goal is to fulfill the user's request.
    
    EXECUTION PLAN:
    1. First, call 'SchemaDiscovery' to find the available data.
    2. Second, call 'SchemaFormatter' to organize that data into our TechnicalSchema.
    3. Finally, call 'QuantAnalyzer' to perform the analysis the user requested.
    
    CRITICAL: You must complete the schema mapping (Steps 1 & 2) before attempting the analysis.
    """,
    # By listing agents here, the Master can delegate to them like tools
    sub_agents=[
        SCHEMA_DISCOVERY_AGENT, 
        SCHEMA_FORMATTER_AGENT, 
        #QUANT_ANALYZER
    ]
)