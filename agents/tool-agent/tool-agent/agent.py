from google.adk.agents import Agent
from .prompts import ROOT_AGENT_INSTRUCTION

root_agent = Agent(
    name="tool-agent",
    model="gemini-2.0-flash",
    description="Greeting agent",
    instruction=ROOT_AGENT_INSTRUCTION
)
