# adk_gsheet_agent/agent.py
import os
import yaml
from datetime import datetime
from typing import List, Any, Dict, Optional, Union

# --- Important: Use vertexai imports for consistency with deploy_agent.py ---
# These imports are for the current Vertex AI SDK for Agents.
from vertexai.preview.agents import Agent
from vertexai.preview.agents import tool_code # For the @tool_code decorator on your tools
from vertexai.generative_models import GenerativeModel # For the LLM model (e.g., Gemini)

# Your custom imports for the Google Sheets agent logic
from adk_gsheet_agent.prompts import ROOT_AGENT_INSTRUCTIONS2, DESCRIPTION2
from adk_gsheet_agent.sheet_tool_provider import SheetToolProvider
from adk_gsheet_agent.agent_dependencies import initialize_agent_dependencies
from adk_gsheet_agent.google_sheet_manager import GoogleSheetManager # For type hints/context if needed


# --- 1. The `create_agent` function (for Remote Deployment) ---
# This function is the designated entry point for Vertex AI Agent Engine deployment.
# It ensures all setup (dependencies, tools, LLM) happens reliably when deployed.
def create_agent(config: Optional[Dict[str, Any]] = None) -> Agent:
    """
    Creates and returns an instance of the Google Sheets ADK Agent.
    This function is explicitly called by the Vertex AI Agent Engine when deploying
    or serving the agent in a managed environment. All agent initialization,
    including tool setup and dependencies, occurs within this function call.
    """
    print(f"[{datetime.now()}] create_agent method called. Initializing agent for remote deployment...")

    # Initialize agent dependencies (e.g., Google Sheets authentication, IDs)
    sheet_manager_deploy, spreadsheet_id_deploy, default_sheet_name_deploy, default_start_expense_row_deploy = initialize_agent_dependencies()

    adk_agent_tools_deploy = []
    if sheet_manager_deploy and sheet_manager_deploy.service:
        try:
            tool_provider_deploy = SheetToolProvider(
                sheet_manager=sheet_manager_deploy,
                spreadsheet_id=spreadsheet_id_deploy,
                default_sheet_name=default_sheet_name_deploy,
                default_start_expense_row=default_start_expense_row_deploy
            )
            adk_agent_tools_deploy = tool_provider_deploy.get_all_tools()
            print(f"[{datetime.now()}] Sheet tools loaded successfully by create_agent for deployment.")
        except Exception as e:
            print(f"ERROR: [{datetime.now()}] create_agent: Could not initialize SheetToolProvider for deployment: {e}. Agent will not have tools.")
    else:
        print(f"WARNING: [{datetime.now()}] create_agent: GoogleSheetManager not ready for deployment. Agent will not have tools.")

    # Instantiate the Generative Model (LLM) here
    llm_model_deploy = GenerativeModel("gemini-2.0-flash")

    # Create the Agent instance
    agent_instance = Agent(
        name="adk_gsheet_agent", # Ensure this name is consistent
        model=llm_model_deploy,
        description=DESCRIPTION2,
        instruction=ROOT_AGENT_INSTRUCTIONS2,
        tools=adk_agent_tools_deploy,
    )
    print(f"[{datetime.now()}] ADK Google Sheet Agent instance created successfully for remote deployment.")
    return agent_instance

# --- 2. Global Agent Instance (for `adk web` local testing) ---
# This block runs when the 'agent.py' module is directly imported (e.g., by 'adk web').
# 'adk web' expects to find the agent object as a global variable.
# We'll use a distinct set of variables to avoid conflicts with the 'create_agent' scope.
print(f"[{datetime.now()}] agent.py: Running global instantiation for adk web compatibility...")

_global_sheet_manager = None
_global_my_spreadsheet_id = None
_global_default_sheet_name = None
_global_default_start_expense_row = None
_global_adk_agent_tools = []
_global_llm_model = None # Placeholder for the global LLM model instance

try:
    # Initialize dependencies globally for adk web
    _global_sheet_manager, _global_my_spreadsheet_id, _global_default_sheet_name, _global_default_start_expense_row = initialize_agent_dependencies()

    if _global_sheet_manager and _global_sheet_manager.service:
        _global_tool_provider = SheetToolProvider(
            sheet_manager=_global_sheet_manager,
            spreadsheet_id=_global_my_spreadsheet_id,
            default_sheet_name=_global_default_sheet_name,
            default_start_expense_row=_global_default_start_expense_row
        )
        _global_adk_agent_tools = _global_tool_provider.get_all_tools()
        print(f"[{datetime.now()}] agent.py: Global Sheet tools loaded successfully for adk web.")
    else:
        print(f"WARNING: [{datetime.now()}] agent.py: Global GoogleSheetManager not ready. adk web might not have access to Google Sheet tools.")

    _global_llm_model = GenerativeModel("gemini-2.0-flash") # Instantiate global LLM model

    # Assign the globally created agent to the 'root_agent' variable
    root_agent: Agent = Agent(
        name="adk_gsheet_agent", # Consistent name
        model=_global_llm_model,
        description=DESCRIPTION2,
        instruction=ROOT_AGENT_INSTRUCTIONS2,
        tools=_global_adk_agent_tools,
    )
    print(f"[{datetime.now()}] agent.py: Global root_agent instantiated for adk web.")

except Exception as e:
    print(f"CRITICAL ERROR: [{datetime.now()}] agent.py: Global root_agent instantiation failed for adk web: {e}")
    # If global instantiation fails, set root_agent to None to prevent errors later.
    root_agent = None