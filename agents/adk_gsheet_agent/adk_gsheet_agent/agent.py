# agent.py
import os
import yaml # NEW: Import yaml library to parse config.yaml
from datetime import datetime
from typing import List, Any, Optional, Union
import random
from adk_gsheet_agent.prompts import ROOT_AGENT_INSTRUCTIONS2, DESCRIPTION2
# Import the new SheetToolProvider class
from adk_gsheet_agent.sheet_tool_provider import SheetToolProvider
# Import ADK components
from google.adk.agents import Agent, LlmAgent # Changed from Agent to LlmAgent for consistency with ADK

# Import the new initialization function
from adk_gsheet_agent.agent_dependencies import initialize_agent_dependencies
from adk_gsheet_agent.google_sheet_manager import GoogleSheetManager # Keep this if you need GoogleSheetManager for type hints or other uses

# --- Global Initialization (Runs ONCE per Cloud Function Cold Start) ---
# Call the initialization function from the separate file to set up shared dependencies
SHEET_MANAGER, MY_SPREADSHEET_ID, DEFAULT_SHEET_NAME, DEFAULT_START_EXPENSE_ROW = initialize_agent_dependencies()


# Only instantiate the tool provider and add tools if the SHEET_MANAGER was successfully created and authenticated
if SHEET_MANAGER and SHEET_MANAGER.service:
    try:
        # Create an instance of your tool provider, passing in the initialized dependencies
        tool_provider = SheetToolProvider(
            sheet_manager=SHEET_MANAGER,
            spreadsheet_id=MY_SPREADSHEET_ID,
            default_sheet_name=DEFAULT_SHEET_NAME,
            default_start_expense_row=DEFAULT_START_EXPENSE_ROW
        )
        # Get all @tool decorated methods from the instance
        adk_agent_tools = tool_provider.get_all_tools()
        print(f"[{datetime.now()}] Sheet tools loaded successfully.")
    except ValueError as e:
        print(f"ERROR: Could not initialize SheetToolProvider: {e}. Agent will not have access to Google Sheet tools.")
    except Exception as e:
        print(f"UNEXPECTED ERROR initializing SheetToolProvider: {e}. Agent will not have access to Google Sheet tools.")
else:
    print("WARNING: GoogleSheetManager not ready from agent_dependencies. Agent will not have access to Google Sheet tools.")



# check this commit to resurrect  https://github.com/mmistroni/Magentic-AlgoTrading101/blob/c945a2b409a8df18caea0249dce75b7a3632d201/agents/my_sheets_agent/my_sheets_agent/agent.py

root_agent = Agent(
    name="adk_ghseet_agent",
    model="gemini-2.0-flash",\
    description=DESCRIPTION2,
    instruction=ROOT_AGENT_INSTRUCTIONS2,
    tools=adk_agent_tools,
)

