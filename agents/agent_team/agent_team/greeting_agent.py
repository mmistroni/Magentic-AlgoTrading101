# @title Import necessary libraries
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For creating message Content/Parts
from agent_team.tools import say_hello
from agent_team.prompts import GREETING_AGENT_INSTRUCTIONS
from agent_team.models import MODEL_CLAUDE_SONNET, OPENROUTER_GPT, GEMINI_FLASH_LITE
import os


model = LiteLlm(
    model=OPENROUTER_GPT,
    api_key=os.getenv('OPENROUTER_API_KEY')
)



greeting_agent = Agent(
    model=model, # Can be a string for Gemini or a LiteLlm object
    name="greeting_agent",
    instruction=GREETING_AGENT_INSTRUCTIONS,
    description="Handles simple greetings and hellos using the 'say_hello' tool.", # Crucial for delegation
    tools=[say_hello], # Pass the function directly
)

print(f"Agent '{greeting_agent.name}' created using model '{model}'.")


