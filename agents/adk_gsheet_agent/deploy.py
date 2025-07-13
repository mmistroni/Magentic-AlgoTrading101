import os
import sys

import vertexai
from absl import app, flags
from dotenv import load_dotenv
from vertexai import agent_engines
from vertexai.preview import reasoning_engines

# --- No direct import of the agent object here. ---
# The agent will be loaded dynamically via AGENT_ENTRYPOINT.

FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket for staging resources.")
flags.DEFINE_string(
    "agent_name", "adk-gsheet-agent", "Name for the deployed Agent Engine resource."
)
flags.DEFINE_string("user_id", "test_user", "User ID for session operations.")
flags.DEFINE_string("session_id", None, "Session ID for operations.")
flags.DEFINE_bool("create", False, "Creates a new deployment.")
flags.DEFINE_bool("delete", False, "Deletes an existing deployment.")
flags.DEFINE_bool("list", False, "Lists all deployments.")
flags.DEFINE_bool("create_session", False, "Creates a new session.")
flags.DEFINE_bool("list_sessions", False, "Lists all sessions for a user.")
flags.DEFINE_bool("get_session", False, "Gets a specific session.")
flags.DEFINE_bool("send", False, "Sends a message to the deployed agent.")
flags.DEFINE_string(
    "message",
    "Can you provide me with the total expenses from Sheet1?",
    "Message to send to the agent.",
)
flags.mark_bool_flags_as_mutual_exclusive(
    [
        "create",
        "delete",
        "list",
        "create_session",
        "list_sessions",
        "get_session",
        "send",
    ]
)

# --- Agent Specifics for Deployment ---
# This path points to the directory containing your agent's 'agent.py' and 'config.yaml'.
# It must be relative to where deploy_agent.py is run (your project root).
AGENT_SOURCE_DIR = "./adk_gsheet_agent"

# This is the fully qualified path to the function within your agent's package
# that Agent Engine will call to instantiate your agent.
# It assumes your main agent definition and the `create_agent` function
# are in 'adk_gsheet_agent/agent.py'.
AGENT_ENTRYPOINT = "adk_gsheet_agent.agent:create_agent"

def create() -> None:
    """Creates a new deployment for the adk_gsheet_agent. 🚀"""
    print(f"Attempting to deploy agent '{FLAGS.agent_name}'...")

    # 1. Instantiate AdkApp.
    # In current Vertex AI SDK versions, AdkApp is a wrapper for deployment,
    # and you DO NOT pass the 'agent' object directly to its constructor.
    app_instance = reasoning_engines.AdkApp(
        enable_tracing=True, # Recommended for visibility in Cloud Trace
    )

    # 2. Deploy to Agent Engine.
    # The 'agent_builder' argument specifies the function that Agent Engine will call
    # to instantiate your agent in the cloud environment.
    remote_app = agent_engines.create(
        agent_engine=app_instance, # The AdkApp instance
        display_name=FLAGS.agent_name.replace('-', ' ').title(), # Generates a user-friendly display name
        resource_id=FLAGS.agent_name, # The unique ID for the deployed agent
        agent_builder=AGENT_ENTRYPOINT, # 🔥 This is the key to fix the TypeError! 🔥
        # Define required Python packages for the deployed environment.
        # This list should include ALL dependencies from your requirements.txt.
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]", # Essential for ADK agents
            "python-dotenv", # Crucial if your agent_dependencies.py loads .env locally
            "pyyaml", # If your agent uses YAML for config
            "google-api-python-client", # For Google Sheets API interactions
            "google-auth-oauthlib", # For authentication with Google APIs
            "google-cloud-secret-manager", # If you're fetching secrets
            # Add any other specific packages your GSheet agent needs here, e.g.:
            # "pandas",
            # "openpyxl",
        ],
        # Include your agent's source directory. This bundles your 'adk_gsheet_agent'
        # directory (containing agent.py, config.yaml, etc.) with the deployment.
        extra_packages=[AGENT_SOURCE_DIR],
        # You can also pass environment variables directly to the deployed agent:
        # env_vars={
        #     "MY_SPREADSHEET_ID": os.getenv("MY_SPREADSHEET_ID"),
        #     "DEFAULT_SHEET_NAME": os.getenv("DEFAULT_SHEET_NAME"),
        #     "GOOGLE_APPLICATION_CREDENTIALS": "/path/to/service-account.json" # Only if service account file