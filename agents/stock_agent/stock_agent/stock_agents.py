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
    SYSTEM MANDATE: You are a JSON converter.
    INPUT DATA: {raw_discovery_results}
    
    TASK: Take the keys from the INPUT DATA and place them into the TechnicalSchema.
    
    STRICT RULES:
    1. USE ONLY the literal strings found in the input. 
    2. NEVER use generic words like 'stock' or 'technical indicators'.
    3. If the input contains 'RSI', the output must contain 'RSI'.
    4. Metadata MUST include the specific field name for the stock identity (e.g., 'symbol' or 'ticker').
    
    If you cannot find specific field names in {raw_discovery_results}, stop and report that the input is empty.
    """,
    output_schema=TechnicalSchema,
    output_key="available_schema"
)

# 2. Specialized Analysis Agent
# It picks up the {available_schema} from the state
# --- The Refined Autonomous Instructions ---
AUTONOMOUS_QUANT_INSTRUCTION = """
**Role**: Senior Quantitative Technical Strategist (Autonomous).
**Objective**: Identify trade candidates by mapping a dynamic schema and analyzing session data.

**Operational Mandate**:
1. **Autonomous Schema Mapping**:
   - You are provided a schema in {available_schema}. You must categorize these fields into 'indicators', 'metadata', and 'volume_flow'.
   - **Identity Rule**: Every technical snapshot REQUIRES a unique identifier (e.g., a symbol or ticker). You must find the field in the schema that represents the stock identity and include it in your 'metadata' list.
   - **Confluence Rule**: To perform a valid analysis, you must identify at least TWO (2) fields that represent technical trends or momentum.

2. **Temporal Logic**:
   - Use `fetch_technical_snapshot_tool` with `target_date='today'` (default) or `target_date='yesterday'`.
   - Do not query specific calendar dates.

3. **Analysis Protocol**:
   - Once the schema is mapped, fetch the data.
   - Cross-reference price action against your identified indicators. 
   - Issue 'BUY' or 'SELL' only if there is confluence. Issue 'HOLD' if the data is contradictory or the identity field is missing.

**Constraint**: Your output MUST satisfy the Pydantic schema validation. If you provide 'price' without an accompanying 'symbol' or 'ticker', the analysis will be rejected.
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