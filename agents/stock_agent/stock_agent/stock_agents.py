from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from stock_agent.tools import (
    discover_technical_schema_tool,
    fetch_technical_snapshot_tool,
)
from stock_agent.models import TechnicalSchema, TrendSignal

# ==========================================
# 1. Specialized Schema Agents & Unit
# ==========================================

# Discover WHAT indicators we can analyze
SCHEMA_DISCOVERY_AGENT = LlmAgent(
    name="SchemaDiscovery",
    model="gemini-2.5-flash",
    instruction="""SYSTEM ROLE: Silent Data Pre-processor.
    TASK: Execute `discover_technical_schema_tool` immediately. 
    OUTPUT: Provide ONLY the raw schema returned by the tool. 
    CONSTRAINT: Do not respond to the user's request for analysis or recommendations. 
    Just provide the schema for the next agent in the pipeline.""",
    tools=[FunctionTool(discover_technical_schema_tool)],
    output_key="raw_discovery_results",
)

# Format the discovered indicators into a structured TechnicalSchema
SCHEMA_FORMATTER_AGENT = LlmAgent(
    name="SchemaFormatter",
    model="gemini-2.5-flash",
    instruction="""
    Convert the raw columns into a TechnicalSchema JSON matching these exact fields:
    - `metadata`: Core fields like ticker, symbol, exchange, cob, or date.
    - `indicators`: Technical indicators like RSI, ADX, SMA, slope, choppiness.
    - `volume_metrics`: Fields related to volume like current_obv, prev_obv, CMF.
    - `beta`: Extract the numeric value or column name for beta if present, otherwise set to null.

    OUTPUT ONLY VALID JSON. NO PREAMBLE. NO EXPLANATION.
    """,
    output_schema=TechnicalSchema,
    output_key="available_schema",
)

SCHEMA_UNIT = SequentialAgent(
    name="SchemaUnit",
    sub_agents=[
        SCHEMA_DISCOVERY_AGENT,
        SCHEMA_FORMATTER_AGENT,
    ],
)


# ==========================================
# 2. Specialized Analysis Agent
# ==========================================

AUTONOMOUS_QUANT_INSTRUCTION = """
## System Instructions: Strategic Stock Analyst

**Role**: Senior Quantitative Analyst. You prioritize **Volume-Price Confirmation** over simple oscillators.

### 1. Indicator Hierarchy
You are provided with technical indicators and optional context parameters:
* **Primary (Trend)**: `SMA20`, `SMA50`, `SMA200`, `slope`, `trend_velocity_gap`.
* **Confirmation (Volume)**: `current_obv`, `prev_obv`, `obv_historical`, `current_cmf`, `previous_cmf`.
* **Filter (Context & Volatility)**: `choppiness`, `spx_choppiness`, `beta` (Optional).
* **Timing (Momentum)**: `RSI`, `demarker`.

### 2. Execution Logic (Strict Gating)

**Step A: Market Regime & Sensitivity (The Filter)**
* **Market Context**: If `choppiness` > 60 OR `spx_choppiness` > 60: Market is "Range-Bound." Do not issue BUY/SELL unless Volume is at a 20-day high (`obv_historical`).
* **Beta Sensitivity (If Present)**:
  - If `beta` > 1.3 (High Volatility): Require BOTH rising OBV trend AND `current_cmf` > 0 to validate BUY.
  - If `beta` < 0.8 (Defensive): Allow BUY on milder CMF signals provided trend bias is strong.
  - If `beta` is Null / Missing: Proceed standardly without modifying validation strictness.

**Step B: Trend Bias (The Direction)**
* **Bullish Bias**: Price > SMA50 AND `slope` > 0.
* **Bearish Bias**: Price < SMA50 AND `slope` < 0.
* **Velocity**: If `trend_velocity_gap` is increasing compared to recent values, the trend is accelerating.

**Step C: Volume Integrity (The Validator)**
* **BUY Condition**: Must have (Bullish Bias) AND (rising OBV trend in `obv_historical` OR `current_cmf` > 0), taking Beta strictness into account.
* **Divergence Warning**: If Price is rising but `current_obv` < `prev_obv`, mark as "Divergent" and issue **HOLD**.

**Step D: Momentum (The Entry/Exit)**
* **Strength Rule**: In a Strong Bullish Bias, ignore RSI "Overbought" (60-75). Only SELL if RSI > 80.
* **Mean Reversion**: In a "Neutral" trend, use RSI < 35 for BUY and RSI > 65 for SELL.

### 3. Output Requirements
For every symbol evaluated, provide:
* **Trend Status**: (Bullish/Bearish/Neutral)
* **Volume Confirmation**: (Confirmed/Divergent/Insufficient Data)
* **Beta Assessment**: Explicitly state the `beta` value if present and its impact on your risk criteria, or note "N/A" if omitted.
* **Final Recommendation**: (BUY/SELL/HOLD)
* **Technical Justification**: Explicitly cite which indicators from the schema drove the decision. Mention if any data was missing (N/A) and how you compensated.
"""

QUANT_ANALYZER = LlmAgent(
    name="QuantAnalyzer",
    model="gemini-2.5-flash",
    instruction=AUTONOMOUS_QUANT_INSTRUCTION,
    tools=[FunctionTool(fetch_technical_snapshot_tool)],
    output_schema=TrendSignal,  # Enforces Pydantic contract from models.py
    output_key="final_trade_signal",
)


# ==========================================
# 3. Main Sequential Pipeline
# ==========================================

TREND_PIPELINE = SequentialAgent(
    name="TrendStrategist",
    sub_agents=[
        SCHEMA_UNIT,  # Step 1: Discover BigQuery columns & format into TechnicalSchema
        QUANT_ANALYZER,  # Step 2: Fetch snapshot data & execute trade signal evaluation
    ],
)