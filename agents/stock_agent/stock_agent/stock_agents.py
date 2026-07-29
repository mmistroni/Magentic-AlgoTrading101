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
# Format the discovered indicators into a structured TechnicalSchema
SCHEMA_FORMATTER_AGENT = LlmAgent(
    name="SchemaFormatter",
    model="gemini-2.5-flash",
    instruction="""
    SYSTEM ROLE: Technical Schema Classifier.
    TASK: You are given a raw list of column names and data types from BigQuery.
    
    Categorize EVERY column into one of these fields:
    - `metadata`: Identification and date columns (e.g., ticker, symbol, exchange, cob, asodate, country, selection, highlight, marketCap, price, open, previousClose, change).
    - `indicators`: Oscillators, moving averages, and technical indicators (e.g., ADX, RSI, SMA20, SMA50, SMA200, slope, choppiness, spx_choppyness, ewo, demarker, fib_161, trend_velocity_gap).
    - `volume_metrics`: Volume-related columns (e.g., current_obv, previous_obv, last_cmf, previous_cmf, obv_last_20_days, cmf_last_20_days).
    - `beta`: If the column name 'beta' is present in the raw column list, set beta equal to the string "beta". Otherwise set to null.

    CRITICAL: DO NOT omit any technical indicator columns. Return valid JSON only.
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

# Agent 2A: Collects data via tools and performs quantitative reasoning (Tools only)
QUANT_ANALYZER = LlmAgent(
    name="QuantAnalyzer",
    model="gemini-2.5-flash",
    instruction=AUTONOMOUS_QUANT_INSTRUCTION,
    tools=[FunctionTool(fetch_technical_snapshot_tool)],
    output_key="quant_analysis_raw",
)

# Agent 2B: Formats raw quant output into strict TrendSignal JSON contract (Schema only)
SIGNAL_FORMATTER_AGENT = LlmAgent(
    name="SignalFormatter",
    model="gemini-2.5-flash",
    instruction="""
    Convert the technical quantitative analysis provided in `quant_analysis_raw` into a valid TrendSignal JSON.
    Ensure all required fields are present:
    - ticker
    - signal (BUY, SELL, or HOLD)
    - confidence_score (float between 0.0 and 1.0)
    - technical_indicators (list of indicators used)
    - fundamental_metrics (list of metrics used, or empty list if none)
    - reasoning (clear explanation of the trade signal)

    OUTPUT ONLY VALID JSON. NO PREAMBLE. NO EXPLANATION.
    """,
    output_schema=TrendSignal,  # Valid: tools=[]
    output_key="final_trade_signal",
)


# ==========================================
# 3. Main Sequential Pipeline
# ==========================================

TREND_PIPELINE = SequentialAgent(
    name="TrendStrategist",
    sub_agents=[
        SCHEMA_UNIT,             # Step 1: Discover BigQuery columns & format into TechnicalSchema
        QUANT_ANALYZER,          # Step 2: Fetch snapshot data & generate quantitative analysis
        SIGNAL_FORMATTER_AGENT,  # Step 3: Format final response into TrendSignal JSON
    ],
)