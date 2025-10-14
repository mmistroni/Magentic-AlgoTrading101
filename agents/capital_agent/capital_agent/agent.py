from .prompts import CAPITAL_AGENT_INSTRUCTION
from .tools import get_capital_city
from google.adk.agents import LlmAgent



capital_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="capital_agent",
    description="Answers user questions about the capital city of a given country.",
    instruction=CAPITAL_AGENT_INSTRUCTION,
    tools=[get_capital_city]
)

root_agent = capital_agent