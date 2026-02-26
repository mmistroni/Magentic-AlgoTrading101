from .prompts import CAPITAL_AGENT_INSTRUCTION
from .tools import get_tfl_route, resolve_date_string
from google.adk.agents import LlmAgent



capital_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="capital_agent",
    description="Answers user questions about the capital city of a given country.",
    instruction=CAPITAL_AGENT_INSTRUCTION,
    tools=[get_tfl_route, resolve_date_string]
)

root_agent = capital_agent