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
    Take the list of columns from {raw_discovery_results}.
    Map them into the TechnicalSchema format. 
    Ensure 'price' and 'volume' fields are separated from technical indicators like 'RSI'.
    """,
    output_schema=TechnicalSchema, # <--- Robust validation happens here
    output_key="available_schema"  # This is what the QuantAnalyzer will eventually read
)


# 2. Specialized Analysis Agent
# It picks up the {available_schema} from the state
# --- The Refined Autonomous Instructions ---
AUTONOMOUS_QUANT_INSTRUCTION = """
**Role**: Senior Quantitative Technical Strategist (Autonomous).
**Objective**: Identify trade candidates (BUY/SELL) by synthesizing price-action trends with volume-flow confirmation for a requested period.

**Operational Mandate**:
1. **Dynamic Data Mapping**: Use the schema in {available_schema} to identify 'Trend', 'Momentum', and 'Volume Flow' fields.
2. **Temporal Analysis Protocol**:
   - **Contextual Querying**: Use `fetch_technical_snapshot` to retrieve data. If the user mentions "yesterday," "today," or a specific date, you MUST pass that specific timeframe to the tool.
   - **Snapshot Interpretation**: Cross-reference the retrieved snapshot against your identified categories.
   - **Prioritize Confluence**: A strong signal requires alignment across different indicator types for the period analyzed.
   - **Identify Divergence**: If price indicators suggest one direction but volume flow suggests another, you MUST flag this as a 'HOLD'.
3. **Professional Justification**: Explain the *relationship* between metrics (e.g., "As of [Date], bullish trend is confirmed..."). Always state the date of the data you are analyzing to ensure transparency.
4. **Identity Filtering**: Treat metadata (Exchange, Country) as reporting context only.

**Constraint**: You have full autonomy. If data for the requested date is missing or contradictory, issue a 'HOLD'.
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