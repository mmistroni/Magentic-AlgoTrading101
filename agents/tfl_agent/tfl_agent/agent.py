from .prompts import TFL_AGENT_INSTRUCTION
from .tools import get_tfl_route, resolve_date_string
from google.adk.agents import LlmAgent



tfl_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="tfl_agent",
    description="Find best route between FAirlop and Bromley.",
    instruction=TFL_AGENT_INSTRUCTION,
    tools=[get_tfl_route, resolve_date_string]
)

root_agent = tfl_agent