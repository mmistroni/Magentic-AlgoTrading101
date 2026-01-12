from google.adk.agents import LlmAgent, SequentialAgent 
from feature_agent.tools import feature_tools
from feature_agent.prompts import FEATURE_AGENT_INSTRUCTION


root_agent =  LlmAgent(
    name="QuantAnalyzer",
    model='gemini-2.5-flash', # Optimized for Dec 2025 multi-step reasoning
    instruction=FEATURE_AGENT_INSTRUCTION,
    tools=feature_tools
)



