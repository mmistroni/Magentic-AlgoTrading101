# @title Import necessary libraries
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts
from agent_team.tools import say_goodbye
from agent_team.prompts import FAREWELL_AGENT_INSTRUCTIONS
from google.adk.models.lite_llm import LiteLlm
from agent_team.models import MODEL_CLAUDE_SONNET, OPENROUTER_GPT
import os

from google.adk.models.lite_llm import LiteLlm

model = LiteLlm(
    model=OPENROUTER_GPT,
    api_key=os.getenv('OPENROUTER_API_KEY')
)

farewell_agent = Agent(
    name="farewell_agent_v1",
    model=model, # Can be a string for Gemini or a LiteLlm object
    description="Handles simple farewells and goodbyes using the 'say_goodbye' tool.",
    instruction=FAREWELL_AGENT_INSTRUCTIONS,
    tools=[say_goodbye], # Pass the function directly
)

print(f"Agent '{farewell_agent}' created using model '{model}'.")


