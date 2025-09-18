from google.adk.agents import LlmAgent
from .prompts import SIGHTSEEING_AGENT_INSTRUCTIONS
# Sightseeing Agent
sagent = LlmAgent(
    model='gemini-2.0-flash',
    name="SightseeingAgent",
    description="Sightseeing information agent",
    instruction=SIGHTSEEING_AGENT_INSTRUCTIONS
)