from google.adk.agents import LlmAgent
from .prompts import TRIPPLANNER_AGENT_INSTRUCTIONS
from .flight_agent import flight_agent
from .sightseeing_agent import sightseeingt_agent
from .hotel_agent import hotel_agent
from google.adk.tools import agent_tool
# Coordinator Agent

flight_tool = agent_tool.AgentTool(flight_agent)
hotel_tool = agent_tool.AgentTool(hotel_agent)
sightseeing_tool = agent_tool.AgentTool(sightseeingt_agent)


root_agent = LlmAgent(
    model='gemini-2.0-flash',
    name="TripPlanner",
    description="Flight booking agent",
    instruction=TRIPPLANNER_AGENT_INSTRUCTIONS,
    tools=[flight_tool, hotel_tool, sightseeing_tool]
)