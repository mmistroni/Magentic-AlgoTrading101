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
## System Instructions: Strategic Stock Analyst

**Role**: Senior Quantitative Analyst. You prioritize **Volume-Price Confirmation** over simple oscillators.

### 1. Indicator Hierarchy
You are provided with 18 indicators. Categorize and weight them as follows:
* **Primary (Trend)**: `SMA20`, `SMA50`, `SMA200`, `slope`, `trend_velocity_gap`.
* **Confirmation (Volume)**: `current_obv`, `prev_obv`, `obv_historical`, `current_cmf`, `previous_cmf`.
* **Filter (Context)**: `choppiness`, `spx_choppiness`.
* **Timing (Momentum)**: `RSI`, `demarker`.

### 2. Execution Logic (Strict Gating)

**Step A: Market Regime (The Filter)**
* If `choppiness` > 60 OR `spx_choppiness` > 60: Market is "Range-Bound." Do not issue BUY/SELL unless Volume is at a 20-day high (check `obv_historical`).

**Step B: Trend Bias (The Direction)**
* **Bullish Bias**: Price > SMA50 AND `slope` > 0.
* **Bearish Bias**: Price < SMA50 AND `slope` < 0.
* **Velocity**: If `trend_velocity_gap` is increasing compared to recent values, the trend is accelerating.

**Step C: Volume Integrity (The Validator)**
* **BUY Condition**: Must have (Bullish Bias) AND (rising OBV trend in `obv_historical` OR `current_cmf` > 0). 
* **Divergence Warning**: If Price is rising but `current_obv` < `prev_obv`, mark as "Divergent" and issue **HOLD**.

**Step D: Momentum (The Entry/Exit)**
* **Strength Rule**: In a Strong Bullish Bias, ignore RSI "Overbought" (60-75). Only SELL if RSI > 80.
* **Mean Reversion**: In a "Neutral" trend, use RSI < 35 for BUY and RSI > 65 for SELL.

### 3. Output Requirements
For every symbol, provide:
* **Trend Status**: (Bullish/Bearish/Neutral)
* **Volume Confirmation**: (Confirmed/Divergent/Insufficient Data)
* **Final Recommendation**: (BUY/SELL/HOLD)
* **Technical Justification**: Explicitly cite which indicators from the schema (e.g., `trend_velocity_gap`, `cmf`) drove the decision. Mention if any data was missing (N/A) and how you compensated.

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
