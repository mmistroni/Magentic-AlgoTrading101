from .prompts import CAPITAL_AGENT_INSTRUCTION
from google.adk.agents import LlmAgent


capital_agent = LlmAgent(
    model="gemini-2.0-flash",
    name="capital_agent",
    description="Answers user questions about the capital city of a given country."
    # instruction and tools will be added next
)