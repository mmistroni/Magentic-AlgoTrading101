from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool
from stock_agent.tools import (
    discover_technical_schema_tool,
    fetch_technical_snapshot_tool,
)
from stock_agent.models import TechnicalSchema, BatchMarketReport

# ==========================================
# 1. Specialized Schema Agents & Unit
# ==========================================

SCHEMA_DISCOVERY_AGENT = LlmAgent(
    name="SchemaDiscovery",
    model="gemini-2.5-flash",
    instruction="""SYSTEM ROLE: Silent Data Pre-processor.
    TASK: Execute `discover_technical_schema_tool` immediately. 
    OUTPUT: Provide ONLY the raw schema returned by the tool.""",
    tools=[FunctionTool(discover_technical_schema_tool)],
    output_key="raw_discovery_results",
)

SCHEMA_FORMATTER_AGENT = LlmAgent(
    name="SchemaFormatter",
    model="gemini-2.5-flash",
    instruction="""
    SYSTEM ROLE: Technical Schema Classifier.
    TASK: Categorize every column from the discovery results into metadata, indicators, volume_metrics, or beta. Return valid JSON only.
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
# 2. Specialized Analysis & Formatting Agents
# ==========================================

AUTONOMOUS_QUANT_INSTRUCTION = """
## System Instructions: Strategic Stock Analyst

**Role**: Senior Quantitative Analyst. You prioritize **Volume-Price Confirmation** over simple oscillators.

### MANDATORY RULE
You MUST process and output an analysis breakdown for **EVERY SINGLE SYMBOL** returned by the `fetch_technical_snapshot_tool`. Do not skip any symbols.

### 1. Indicator Hierarchy
* **Primary (Trend)**: `SMA20`, `SMA50`, `SMA200`, `slope`, `trend_velocity_gap`.
* **Confirmation (Volume)**: `current_obv`, `prev_obv`, `obv_historical`, `current_cmf`, `previous_cmf`.
* **Filter (Context & Volatility)**: `choppiness`, `spx_choppiness`, `beta` (Optional).
* **Timing (Momentum)**: `RSI`, `demarker`.

### 2. Execution Logic (Strict Gating)
* **Market Regime**: If `choppiness` > 60 or `spx_choppiness` > 60, market is Range-Bound (require 20-day high volume for action).
* **Beta Sensitivity**: If `beta` > 1.3, require BOTH rising OBV and `current_cmf` > 0 to BUY. If `beta` < 0.8, allow milder CMF signals.
* **Trend Bias**: Bullish if Price > SMA50 and slope > 0. Bearish if Price < SMA50 and slope < 0.
* **Divergence**: If price rises while `current_obv` falls, flag as Divergent and issue HOLD.

### 3. Output Requirements
Provide a clear analysis breakdown for every symbol so the downstream formatter can accurately map them.
"""

QUANT_ANALYZER = LlmAgent(
    name="QuantAnalyzer",
    model="gemini-2.5-flash",
    instruction=AUTONOMOUS_QUANT_INSTRUCTION,
    tools=[FunctionTool(fetch_technical_snapshot_tool)],
    output_key="quant_analysis_raw",
)

# Uses the BatchMarketReport container model from models.py
SIGNAL_FORMATTER_AGENT = LlmAgent(
    name="SignalFormatter",
    model="gemini-2.5-flash",
    instruction="""
    SYSTEM ROLE: JSON Serialization Specialist.
    TASK: Read the multi-ticker quantitative analysis from `quant_analysis_raw` and map every single evaluated ticker into the `BatchMarketReport` schema structure.
    
    CONSTRAINTS:
    - Ensure every ticker has a clear `signal` (BUY, SELL, or HOLD).
    - Provide a robust numerical `confidence_score` between 0.0 and 1.0.
    - Populate `reasoning` explicitly based on the analysis text.
    - OUTPUT ONLY VALID JSON MATCHING THE SCHEMA. NO PREAMBLE.
    """,
    output_schema=BatchMarketReport,
    output_key="final_trade_signal",
)


# ==========================================
# 3. Main Sequential Pipeline
# ==========================================

TREND_PIPELINE = SequentialAgent(
    name="TrendStrategist",
    sub_agents=[
        SCHEMA_UNIT,             # Step 1: Discover & categorize BigQuery columns
        QUANT_ANALYZER,          # Step 2: Fetch snapshot data & run quantitative rules
        SIGNAL_FORMATTER_AGENT,  # Step 3: Compile into a strict JSON list format via BatchMarketReport
    ],
)