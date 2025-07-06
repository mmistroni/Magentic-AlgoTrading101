from google.adk.agents import Agent
from my_sheet_agent.prompts import ROOT_AGENT_INSTRUCTION
from my_sheet_agent.tools.character_counter import count_characters

root_agent = Agent(
    name="my_sheet_agent",
    model="gemini-2.0-flash",
    description="A bot that shortens messages while maintaining their core meaning",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[count_characters],
)