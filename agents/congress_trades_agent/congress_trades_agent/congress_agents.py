from google.adk.agents import LlmAgent, SequentialAgent 
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.tools import FunctionTool

# Import from our modules
# Import from our modules
from .tools import fetch_congress_signals_tool, check_fundamentals_tool
from .extra_tools import fetch_form4_signals_tool, fetch_lobbying_signals_tool
from .prompts import RESEARCHER_INSTRUCTION, TRADER_INSTRUCTION, INSIDER_ANALYST_INSTRUCTION

# ==========================================
# AGENT 1: The Researcher
# ==========================================
congress_researcher = LlmAgent(
    name="CongressResearcher",
    model='gemini-2.5-flash',
    instruction=RESEARCHER_INSTRUCTION,
    tools=[
        FunctionTool(fetch_congress_signals_tool)  # <-- Kicks off the pipeline, grabs the tickers!
    ],
    output_key="political_context" 
)

# ==========================================
# AGENT 2: The Insider Analyst
# ==========================================
insider_analyst = LlmAgent(
    name="CorporateInsiderAnalyst",
    model='gemini-2.5-flash',
    instruction=INSIDER_ANALYST_INSTRUCTION,
    tools=[
        FunctionTool(fetch_lobbying_signals_tool), # <-- Checks Lobbying on the tickers
        FunctionTool(fetch_form4_signals_tool)     # <-- Checks Insiders on the tickers
    ],
    output_key="political_and_insider_context"
)

# ==========================================
# AGENT 3: The Trader
# ==========================================
congress_trader = LlmAgent(
    name="CongressTrader",
    model='gemini-2.5-flash',
    instruction=TRADER_INSTRUCTION,
    tools=[
        FunctionTool(check_fundamentals_tool),     # <-- Checks P/E, Debt, and makes final decision
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
        insider_analyst,
        congress_trader
    ]
)