# agent.py
import os
import yaml # NEW: Import yaml library to parse config.yaml
from datetime import datetime
from typing import List, Any, Optional, Union
import random
from adk_gsheet_agent.prompts import ROOT_AGENT_INSTRUCTIONS, DESCRTPTION

# Import ADK components
from google.adk.agents import Agent, LlmAgent # Changed from Agent to LlmAgent for consistency with ADK

# Import your GoogleSheetManager and get_secret helper
#from google_sheet_manager import GoogleSheetManager, get_secret

def get_dad_jokes():
    jokes = [
    "What do you call fake spaghetti? An impasta",
    "Why did the scarecrow win an award? Because he was outstanding in his field",
    "Why did the chicken cross the road? to get to the  other side!",
    "What do you call a belt made of watches? a waist of time",
    ]

    return random.choice(jokes)

# --- Define ADK Tools (Wrapper Functions) ---
adk_agent_tools = [get_dad_jokes] # This list will hold the functions provided to the ADK Agent


root_agent = Agent(
    name="dad_joke_agent",
    model="gemini-2.0-flash",\
    description="Dad Joke Agent",
    instruction=ROOT_AGENT_INSTRUCTIONS,
    tools=[get_dad_jokes],
)

