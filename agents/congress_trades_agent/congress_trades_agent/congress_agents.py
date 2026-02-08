from google.adk.agents import LlmAgent, SequentialAgent 
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

# Import from our modules
from .tools import fetch_congress_signals_tool, check_fundamentals_tool
from .prompts import RESEARCHER_INSTRUCTION, TRADER_INSTRUCTION

# ==========================================
# AGENT 1: The Researcher
# ==========================================
# Its job is to create the "political_context" key for the next agent.
congress_researcher = LlmAgent(
    name="CongressResearcher",
    model='gemini-2.5-flash',
    instruction=RESEARCHER_INSTRUCTION,
    # In ADK, we usually don't need tools here if it relies on built-in knowledge 
    # or a specific search tool you have available in ADK.
    output_key="political_context" 
)

# ==========================================
# AGENT 2: The Trader
# ==========================================
# It picks up 'political_context' automatically from the sequential state.
congress_trader = LlmAgent(
    name="CongressTrader",
    model='gemini-2.5-flash',
    instruction=TRADER_INSTRUCTION,
    tools=[
        FunctionTool(fetch_congress_signals_tool),
        FunctionTool(check_fundamentals_tool)
    ],
    output_key="final_trade_plan"
)

# ==========================================
# THE PIPELINE
# ==========================================
CONGRESS_PIPELINE = SequentialAgent(
    name="CongressTradingStrategy",
    sub_agents=[
        congress_researcher,
        congress_trader
    ]
)
