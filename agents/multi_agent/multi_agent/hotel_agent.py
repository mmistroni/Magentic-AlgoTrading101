from google.adk.agents import LlmAgent
# Hotel Agent
from .prompts import HOTEL_AGENT_INSTRUCTIONS
# Flight Agent
hagent = LlmAgent(
    model='gemini-2.0-flash',
    name="HotelAgent",
    description="Hotel booking agent",
    instruction=HOTEL_AGENT_INSTRUCTIONS
)