from google.adk.agents import Agent
from .prompts import ROOT_AGENT_INSTRUCTION

root_agent = Agent(
    name="greeting-agent",
    model="gemini-2.0-flash",
    description="A bot that shortens messages while maintaining their core meaning",
    instruction=ROOT_AGENT_INSTRUCTION
)
