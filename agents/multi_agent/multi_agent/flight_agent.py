from google.adk.agents import LlmAgent
from .prompts import FLIGHT_AGENT_INSTRUCTIONS
# Flight Agent
flight_agent = LlmAgent(
    model='gemini-2.0-flash',
    name="FlightAgent",
    description="Flight booking agent",
    instruction=FLIGHT_AGENT_INSTRUCTIONS
)