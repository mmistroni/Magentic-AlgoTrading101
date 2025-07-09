# agent.py
import os
import yaml # NEW: Import yaml library to parse config.yaml
from datetime import datetime
from typing import List, Any, Optional, Union
import random
from adk_gsheet_agent.prompts import ROOT_AGENT_INSTRUCTIONS, DESCRTPTION
# Import ADK components
from google.adk.agents import Agent, LlmAgent # Changed from Agent to LlmAgent for consistency with ADK

# Import the new initialization function
from agent_dependencies import initialize_agent_dependencies
from google_sheet_manager import GoogleSheetManager # Keep this if you need GoogleSheetManager for type hints or other uses

# --- Global Initialization (Runs ONCE per Cloud Function Cold Start) ---
# Call the initialization function from the separate file to set up shared dependencies
SHEET_MANAGER, MY_SPREADSHEET_ID, DEFAULT_SHEET_NAME, DEFAULT_START_EXPENSE_ROW = initialize_agent_dependencies()



# Import your GoogleSheetManager and get_secret helper
#from google_sheet_manager import GoogleSheetManager, get_secret
# check this commit to resurrect  https://github.com/mmistroni/Magentic-AlgoTrading101/blob/c945a2b409a8df18caea0249dce75b7a3632d201/agents/my_sheets_agent/my_sheets_agent/agent.py
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
    name="adk_ghseet_agent",
    model="gemini-2.0-flash",\
    description="An intelligent AI assistant specialized in managing personal budgets within a Google Sheet. It can add new expenses, retrieve financial summaries, list past transactions, and provide insights into daily spending.",
    instruction=ROOT_AGENT_INSTRUCTIONS,
    tools=[get_dad_jokes],
)

