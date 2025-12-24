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
    ROLE: You are a strict DATA TRANSFORMATION layer. 
    TASK: Regardless of what the user eventually wants to analyze, you MUST map the keys found in {raw_discovery_results} into the TechnicalSchema.
    COLUMNS TO PROCESS: {raw_discovery_results}
    Identify and categorize the columns from {raw_discovery_results} using these logic rules:
    
    1. **Metadata**: Any field that identifies the stock (e.g., ticker, symbol, name) or basic price info (price, open, close).
    2. **Indicators**: Any field that represents a technical study. Usually these are uppercase (RSI, ADX) or contain numbers (SMA20, EMA50). If you are unsure and it's a numeric technical value, put it here.
    3. **Volume**: Anything containing 'volume', 'obv', or 'flow'.
    
    **Constraint**: You MUST NOT return empty lists. If columns exist in the input, they MUST be categorized.
    
    """,
    output_schema=TechnicalSchema, # <--- Robust validation happens here
    output_key="available_schema"  # This is what the QuantAnalyzer will eventually read
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
TREND_PIPELINE = SequentialAgent(
    name="TrendPipeline",
    sub_agents=[
        SCHEMA_DISCOVERY_AGENT,
        SCHEMA_FORMATTER_AGENT, 
        QUANT_ANALYZER
    ]
)