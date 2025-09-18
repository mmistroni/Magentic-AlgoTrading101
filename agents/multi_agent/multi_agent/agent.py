from google.adk.agents import LlmAgent
from .prompts import TRIPPLANNER_AGENT_INSTRUCTIONS
from .flight_agent import fagent
from .sightseeing_agent import sagent
from .hotel_agent import hagent
from google.adk.tools import agent_tool
# Coordinator Agent

flight_tool = agent_tool.AgentTool(fagent)
hotel_tool = agent_tool.AgentTool(hagent)
sightseeing_tool = agent_tool.AgentTool(sagent)


root_agent = LlmAgent(
    model='gemini-2.0-flash',
    name="TripPlanner",
    description="Flight booking agent",
    instruction=TRIPPLANNER_AGENT_INSTRUCTIONS,
    tools=[flight_tool, hotel_tool, sightseeing_tool]
)