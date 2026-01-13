from google.adk.agents import LlmAgent, SequentialAgent 
from feature_agent.tools import fetch_consensus_holdings_tool, \
                                get_forward_return_tool,\
                                get_technical_metrics_tool
  
from feature_agent.prompts import FEATURE_AGENT_INSTRUCTION
from google.adk.tools import FunctionTool


CONSENSUS_FT = FunctionTool(fetch_consensus_holdings_tool)
FW_RETURNS_FT = FunctionTool(get_forward_return_tool) 
TECH_METRICS_FT = FunctionTool(get_technical_metrics_tool) 



root_agent =  LlmAgent(
    name="QuantAnalyzer",
    model='gemini-2.5-flash', # Optimized for Dec 2025 multi-step reasoning
    instruction=FEATURE_AGENT_INSTRUCTION,
    tools=[CONSENSUS_FT, FW_RETURNS_FT, TECH_METRICS_FT]
)



