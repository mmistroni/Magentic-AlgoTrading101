from google.adk.agents import LlmAgent
from .prompts import TRIPPLANNER_AGENT_INSTRUCTIONS
from .flight_agent import flight_agent
from .sightseeing_agent import sightseeingt_agent
from .hotel_agent import hotel_agent
# Coordinator Agent

root_agent = LlmAgent(
    model='gemini-2.0-flash',
    name="TripPlanner",
    description="Flight booking agent",
    instruction=TRIPPLANNER_AGENT_INSTRUCTIONS,
    sub_agents=[flight_agent, hotel_agent, sightseeingt_agent]
)