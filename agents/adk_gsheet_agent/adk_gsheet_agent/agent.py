import os
import yaml
from datetime import datetime
from typing import List, Any, Optional, Union, Dict

# --- Core ADK Agent Imports (from google.adk) ---
try:
    from google.adk.agents import Agent, LlmAgent
    # tool_code is NOT imported directly here, as it causes ImportError for google-adk==1.6.1 in your environment.
    # Tools will be defined using FunctionTool directly by SheetToolProvider.
    _ADK_IMPORTS_SUCCESS = True
    print(f"[{datetime.now()}] agent.py: Successfully imported Agent and LlmAgent from google.adk.agents.")
except ImportError as e:
    _ADK_IMPORTS_SUCCESS = False
    print(f"CRITICAL IMPORT ERROR: [{datetime.now()}] agent.py: Failed to import from google.adk.agents: {e}")
    print("Ensure 'google-adk' is installed and its version is compatible.")


# --- Vertex AI Generative Model Import (from vertexai) ---
try:
    from vertexai.generative_models import GenerativeModel
    import vertexai
    _VERTEXAI_MODEL_IMPORT_SUCCESS = True
    print(f"[{datetime.now()}] agent.py: Successfully imported GenerativeModel from vertexai.")
except ImportError as e:
    _VERTEXAI_MODEL_IMPORT_SUCCESS = False
    print(f"CRITICAL IMPORT ERROR: [{datetime.now()}] agent.py: Failed to import GenerativeModel from vertexai: {e}")
    print("Ensure 'google-cloud-aiplatform' is installed.")


# Your custom imports
from adk_gsheet_agent.prompts import ROOT_AGENT_INSTRUCTIONS2, DESCRIPTION2
from adk_gsheet_agent.sheet_tool_provider import SheetToolProvider
from adk_gsheet_agent.agent_dependencies import initialize_agent_dependencies
from adk_gsheet_agent.google_sheet_manager import GoogleSheetManager


# --- Global variable for the agent instance (primarily for adk web) ---
root_agent: Optional[LlmAgent] = None

print(f"[{datetime.now()}] create_agent called for remote deployment.")

if not (_ADK_IMPORTS_SUCCESS and _VERTEXAI_MODEL_IMPORT_SUCCESS):
    raise RuntimeError("Required ADK or Vertex AI imports failed. Cannot create agent.")

# Initialize Vertex AI for the deployed agent's context.
# Agent Engine typically sets these environment variables.
project_id = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID")
location = os.getenv("GOOGLE_CLOUD_LOCATION") or os.getenv("GCP_REGION")
if project_id and location:
    vertexai.init(project=project_id, location=location)
    print(f"[{datetime.now()}] vertexai.init() called within create_agent for Project: {project_id}, Location: {location}")
else:
    print(f"WARNING: [{datetime.now()}] Project ID or Location not found in environment for create_agent. Agent Engine should provide this automatically.")


sheet_manager, spreadsheet_id, default_sheet_name, default_start_expense_row = initialize_agent_dependencies()

adk_agent_tools = []
if sheet_manager and sheet_manager.service:
    # SheetToolProvider will directly use FunctionTool internally.
    tool_provider = SheetToolProvider(
        sheet_manager=sheet_manager,
        spreadsheet_id=spreadsheet_id,
        default_sheet_name=default_sheet_name,
        default_start_expense_row=default_start_expense_row,
    )
    adk_agent_tools = tool_provider.get_all_tools()
    print(f"[{datetime.now()}] Remote Sheet tools loaded successfully for deployment.")
else:
    print(f"WARNING: [{datetime.now()}] GoogleSheetManager not ready in create_agent. Agent will not have access to Google Sheet tools.")

# Pass the model name as a string, not the GenerativeModel object
agent_instance = LlmAgent(
    name="adk_gsheet_agent_deployed",
    model="gemini-2.0-flash", # <--- Corrected: Pass model name as string
    description=DESCRIPTION2,
    instruction=ROOT_AGENT_INSTRUCTIONS2,
    tools=adk_agent_tools,
)

root_agent = agent_instance
print(f"[{datetime.now()}] Agent instance created by create_agent for deployment.")
# --- Global Initialization & Agent Instantiation (for `adk web` local testing) ---
# This block runs once when adk_gsheet_agent/agent.py is first loaded (e.g., by `adk web`).
print(f"[{datetime.now()}] agent.py: Running global initialization for adk web compatibility...")


