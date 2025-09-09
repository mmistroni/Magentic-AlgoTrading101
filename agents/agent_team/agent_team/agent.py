# @title Import necessary libraries
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts
from agent_team.tools import get_weather
from agent_team.prompts import WEATHER_AGENT_INSTRUCTIONS
from google.adk.models.lite_llm import LiteLlm
from agent_team.models import OPENROUTER_GPT
from agent_team.farewell_agent import farewell_agent
from agent_team.greeting_agent import greeting_agent
import os
from google.adk.models.lite_llm import LiteLlm

liteLlmModel = LiteLlm(
    model=OPENROUTER_GPT,
    api_key=os.getenv('OPENROUTER_API_KEY')
)



root_agent = Agent(
    name="weather_agent_v1",
    model=liteLlmModel, # Can be a string for Gemini or a LiteLlm object
    description="The main coordinator agent. Handles weather requests and delegates greetings/farewells to specialists.",
    instruction=WEATHER_AGENT_INSTRUCTIONS,
    tools=[get_weather], # Pass the function directly,
    # Key change: Link the sub-agents here!
    sub_agents=[greeting_agent, farewell_agent]
)

print(f"Agent '{root_agent.name}' created using model '{liteLlmModel}'.")


