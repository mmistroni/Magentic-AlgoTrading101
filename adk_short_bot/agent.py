from google.adk.agents import Agent
from .adk_short_bot.prompts import ROOT_AGENT_INSTRUCTIONS
from .tools import count_characters


root_agent = Agent(
    name="adk_short_bot",
    model="gemini-2.0-flash",
    description="A bot that shortens message while  maintaining their core meaning",
    instructions=ROOT_AGENT_INSTRUCTIONS,
    tools=[count_characters],
)