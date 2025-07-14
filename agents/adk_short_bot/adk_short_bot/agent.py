from google.adk.agents import Agent
from adk_short_bot.prompts import ROOT_AGENT_INSTRUCTION
from adk_short_bot.tools.character_counter import count_characters

short_agent = Agent(
    name="adk_short_bot",
    model="gemini-2.0-flash",
    description="A bot that shortens messages while maintaining their core meaning",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[count_characters],
)

root_agent = short_agent