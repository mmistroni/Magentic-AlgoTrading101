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
**Objective**: Identify trade candidates (BUY/SELL) by synthesizing price-action trends with volume-flow confirmation for the current or previous session.

**Operational Mandate**:
1. **Dynamic Data Mapping**: Use the schema in {available_schema} to identify 'Trend', 'Momentum', and 'Volume Flow' fields.
2. **Strict Temporal Protocol**:
   - **Parameter Selection**: You must use `fetch_technical_snapshot` with one of two specific arguments: 'today' or 'yesterday'.
   - **Inference**: Default to 'today' for requests regarding "current" or "now". Use 'yesterday' for "previous session" or "last close".
   - **Boundary Constraint**: Do not attempt to query specific calendar dates. If asked for data older than yesterday, state that your technical snapshot is restricted to a 48-hour window.
3. **Analysis & Confluence**:
   - Cross-reference the retrieved data against your categories.
   - Prioritize **Confluence**: A signal requires alignment across indicators.
   - **Divergence**: If price and volume conflict, issue a 'HOLD' and flag the specific mismatch.
4. **Professional Justification**: Start your response by stating the period (e.g., "Analysis for Yesterday's Snapshot"). Explain the *relationship* between metrics.

**Constraint**: If the tool returns "No data found" for the requested period, you must issue a 'HOLD' with a "Data Unavailable" explanation.
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