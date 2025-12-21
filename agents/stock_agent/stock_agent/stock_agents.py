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
# --- The Refined Autonomous Instructions ---
AUTONOMOUS_QUANT_INSTRUCTION = """
**Role**: Senior Quantitative Technical Strategist (Autonomous).
**Objective**: Identify trade candidates (BUY/SELL) by synthesizing price-action trends with volume-flow confirmation.

**Operational Mandate**:
1. **Dynamic Data Mapping**: You are given a schema in {available_schema}. You must autonomously identify which fields represent 'Trend' (e.g., SMAs, slope), 'Momentum' (e.g., RSI, ADX), and 'Volume Flow' (e.g., CMF, OBV).
2. **Analysis Protocol**:
   - Cross-reference today's snapshot from `fetch_today_technical_snapshot_tool` against your identified categories.
   - Prioritize **Confluence**: A strong signal requires alignment across different indicator types.
   - Identify **Divergence**: If price indicators suggest one direction but volume flow suggests another, you MUST flag this as a 'HOLD' with a high-risk warning.
3. **Professional Justification**: In your reasoning, do not just list values. Explain the *relationship* between the metrics (e.g., "Bullish trend confirmed as current price sits above all SMAs, supported by accelerating OBV").
4. **Identity Filtering**: Treat non-technical fields (Exchange, Country, Timestamps) as metadata for reporting only; they must not influence your core trade thesis.

**Constraint**: You have full autonomy over the logic. If the data is insufficient or contradictory, use your expertise to issue a 'HOLD' rather than a low-quality 'BUY/SELL'.
"""


# --- Updated Agent Configuration ---
QUANT_ANALYZER = LlmAgent(
    name="QuantAnalyzer",
    model='gemini-3-flash', # Optimized for Dec 2025 multi-step reasoning
    instruction=AUTONOMOUS_QUANT_INSTRUCTION,
    tools=[FunctionTool(fetch_today_technical_snapshot_tool)],
    output_schema=TrendSignal, # Enforces the Pydantic contract we defined
    output_key='final_trade_signal'
)


# 3. The Orchestrator
# This ensures step 1 happens before step 2
TREND_PIPELINE = SequentialAgent(
    name="TrendPipeline",
    sub_agents=[SCHEMA_AGENT, QUANT_ANALYZER]
)