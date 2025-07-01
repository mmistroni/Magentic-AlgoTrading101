import logging
from google.cloud import secretmanager
import os
import json
import vertexai
from vertexai import agent_engines
from google.oauth2 import service_account
import google.api_core.exceptions # For more specific error handling

ADK_AGENT_URL_SECRET_NAME = "projects/682143946483/secrets/ADK-AGENT-URL"

PROJECT_ID = os.environ.get('GOOGLE_PROJECT_ID')
LOCATION = os.environ.get('GOOGLE_AGENT_LOCATION', "us-central1")
project_number = "682143946483" # Replace with your actual project number if different
secret_id = "ADK-AGENT-URL" # Replace with your actual secret name
# Construct the full resource name including the version
# Using 'latest' is generally recommended for production
ADK_AGENT_URL_SECRET_NAME = f"projects/{project_number}/secrets/{secret_id}/versions/latest"
GOOGLE_CREDENTIALS_URL = f"projects/{project_number}/secrets/GOOGLE_SHEETS_CREDENTIALS/versions/latest"
# Initialize Secret Manager client outside the function to reuse it
# This avoids re-initializing the client for every function invocation
secret_client = secretmanager.SecretManagerServiceClient()
_creds = None
_remote_agent = None
secret_client = None # Will be initialized below after the import
credStatus = 'InitCreds'
agentStatus = 'InitAgent'

def _get_secret_variable(secret_var_name):
    try:
        response = secret_client.access_secret_version(name=secret_var_name)
        adk_agent_endpoint = response.payload.data.decode("UTF-8")
        logging.info(f'Successfully accessed secret: {secret_id}')
    except Exception as e:
        logging.error(f'Failed to access secret {secret_id}: {str(e)}') # Use error level for failures
        adk_agent_endpoint = "ERROR: Failed to retrieve secret" # Assign a default or handle appropriately
        # Optionally re-raise if this is a critical error for the function
        # raise e
    return adk_agent_endpoint

def _initialize_vertex_ai_agent():
    """
    Initializes Vertex AI and loads the Agent Engine agent.
    This function is designed to be called once globally during a Cloud Function's
    cold start, and subsequent calls will return immediately if already initialized.
    """
    global _creds, _remote_agent
    agentStatus = 'attempting'
    FQN_AGENT_ID = _get_secret_variable(ADK_AGENT_URL_SECRET_NAME)
    # If the agent is already loaded, no need to re-initialize
    if _remote_agent is not None:
        agentStatus = 'Loaded'
        return
    else :
        agentStatus = 'ToBeLoaded'
    # Ensure required environment variables are set
    if not PROJECT_ID or not FQN_AGENT_ID:
        raise ValueError(
            "Environment variables GOOGLE_PROJECT_ID or GOOGLE_AGENT_FQN are not set. "
            "Please configure them in your Cloud Function deployment."
        )

    # Load credentials from the environment variable (expected to be a JSON string)
    credentials_json_str = _get_secret_variable('GOOGLE_SHEET_CREDENTIALS') # This name is from your provided code
    if not credentials_json_str:
        credStatus = 'CAnnot load'
        #raise ValueError(
        #    "GOOGLE_SHEET_CREDENTIALS environment variable not set. "
        #    "It should contain the JSON string of your service account key."
        #)
    try:
        credentials_info = json.loads(credentials_json_str)
        _creds = service_account.Credentials.from_service_account_info(credentials_info)
        credStatus = 'Loaded'
    except json.JSONDecodeError as e:
        credStatus = 'Failed'
        #raise ValueError(f"Failed to parse GOOGLE_SHEET_CREDENTIALS as JSON: {e}")

    # Initialize Vertex AI SDK
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        credentials=_creds,
    )
    print(f"Vertex AI initialized for project: {PROJECT_ID}, location: {LOCATION}")

    # Get the Agent Engine object
    try:
        _remote_agent = agent_engines.get(FQN_AGENT_ID)
        print(f"Successfully retrieved agent: {FQN_AGENT_ID}")
        agentStatus = 'Connected'
    except google.api_core.exceptions.NotFound as e:
        raise RuntimeError(
            f"Agent with FQN '{FQN_AGENT_ID}' not found. "
            f"Please verify GOOGLE_AGENT_FQN is correct and the agent is deployed in '{LOCATION}'. Details: {e}"
        )
    except Exception as e:
        raise RuntimeError(f"Failed to get remote agent: {e}")


# Call the initialization function once when the script module is loaded.
# This ensures that on a warm start of the Cloud Function, the agent is already ready.
try:
    _initialize_vertex_ai_agent()
    #pass
except Exception as e:
    # Log the error during global initialization.
    # The Cloud Function will still attempt to deploy, but invocations will fail
    # if the agent initialization was unsuccessful.
    logging.info(f"Global Vertex AI Agent initialization failed: {e}")
    agentStatus = str(e)

def execute_call(request): 
    """Responds to any HTTP request.
    Args:
        request (flask.Request): The request object.
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`.
    """
    request_json = request.get_json(silent=True)
    request_args = request.args
    logging.info('Attempting to access agent url')

    
    # --- Your original try-except block ---
    
    adk_agent_endpoint = _get_secret_variable(ADK_AGENT_URL_SECRET_NAME)

    if request_json and 'name' in request_json:
        name = request_json['name']
    elif request_args and 'name' in request_args:
        name = request_args['name']
    else:
        name = 'World'
    return f'Hello {name}! Nice to see you again attempting. you should have accessed {adk_agent_endpoint}@{PROJECT_ID}@{LOCATION} {credStatus} {agentStatus}'