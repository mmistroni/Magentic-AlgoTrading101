import os
import random
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm
from .prompts import ROOT_AGENT_INSTRUCTION

model = LiteLlm(
    model="openrouter/openai/gpt-4.1",
    api_key=os.getenv('OPENROUTER_API_KEY')
)

def get_dad_jokes():
    jokes = [
    "What do you call fake spaghetti? An impasta",
    "Why did the scarecrow win an award? Because he was outstanding in his field",
    "Why did the chicken cross the road? to get to the  other side!",
    "What do you call a belt made of watches? a waist of time",
    ]

    return random.choice(jokes)




root_agent = Agent(
    name="dad_joke_agent",
    model=model,
    description="Dad Joke Agent",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[get_dad_jokes],
)
