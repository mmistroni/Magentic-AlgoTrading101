import logging
from google.cloud import secretmanager
import os
import json
import vertexai
from vertexai import agent_engines
from google.oauth2 import service_account
import google.api_core.exceptions # For more specific error handlinglo

# Set up logging for Cloud Functions
logging.basicConfig(level=logging.INFO)

# --- Configuration Constants ---
# It's better to use GOOGLE_CLOUD_PROJECT from env, and default if not found
PROJECT_ID = os.environ.get('GOOGLE_CLOUD_PROJECT', "682143946483") # Use PROJECT_ID as a fallback default
LOCATION = os.environ.get('GOOGLE_AGENT_LOCATION', "us-central1")

# Construct full secret resource names using the determined PROJECT_ID
ADK_AGENT_URL_SECRET_NAME = f"projects/{PROJECT_ID}/secrets/ADK-AGENT-URL/versions/latest"
GOOGLE_SHEETS_CREDENTIALS_SECRET_NAME = f"projects/{PROJECT_ID}/secrets/GOOGLE_SHEET_CREDENTIALS/versions/latest"

# --- Global Variables for Warm Starts ---
secret_client = None # Lazily initialize Secret Manager client
_creds = None
_remote_agent = None
_initialization_error = None # To store any global initialization error status

# --- Helper Functions ---
def _get_secret_variable(secret_full_name: str) -> str:
    """Accesses a secret version from Secret Manager."""
    global secret_client
    if secret_client is None:
        print("Initializing Secret Manager client globally.")
        secret_client = secretmanager.SecretManagerServiceClient()

    try:
        response = secret_client.access_secret_version(name=secret_full_name)
        # Log the secret ID, which is the 6th element in the split full name
        secret_id_for_log = secret_full_name.split('/')[5] if len(secret_full_name.split('/')) > 5 else secret_full_name
        print(f'Successfully accessed secret: {secret_id_for_log}')
        return response.payload.data.decode("UTF-8")
    except google.api_core.exceptions.NotFound:
        print(f'Secret not found: {secret_full_name}. Check secret name, project, and permissions.')
        raise ValueError(f"Secret '{secret_full_name.split('/')[5]}' not found or inaccessible.")
    except Exception as e:
        print(f'Failed to access secret {secret_full_name}: {e}')
        raise RuntimeError(f"Failed to retrieve secret '{secret_full_name.split('/')[5]}': {e}")


def _initialize_vertex_ai_agent():
    """
    Initializes Vertex AI and loads the Agent Engine agent.
    Designed to be called once globally during a Cloud Function's cold start.
    """
    global _creds, _remote_agent # Declare globals to modify them

    # If the agent is already loaded (from a warm start), no need to re-initialize
    if _remote_agent is not None:
        print("Agent already initialized from a warm start. Skipping re-initialization.")
        return

    print("Performing cold start initialization for Vertex AI Agent.")

    # 1. Get Agent FQN from Secret Manager
    FQN_AGENT_ID = _get_secret_variable(ADK_AGENT_URL_SECRET_NAME)
    if not FQN_AGENT_ID or FQN_AGENT_ID.startswith("ERROR:"): # Error string from _get_secret_variable if it didn't raise
         raise ValueError(f"Failed to retrieve Agent FQN from secret: {FQN_AGENT_ID}")


    # 2. (Optional) Load Google Sheets Credentials from Secret Manager
    # ONLY if they are genuinely needed for Vertex AI operations, otherwise remove.
    # If they are just for Sheets, load them into _creds, but don't pass to vertexai.init
    try:
        credentials_json_str = _get_secret_variable(GOOGLE_SHEETS_CREDENTIALS_SECRET_NAME)
        if credentials_json_str and not credentials_json_str.startswith("ERROR:"):
            credentials_info = json.loads(credentials_json_str)
            _creds = service_account.Credentials.from_service_account_info(credentials_info)
            print("Google Sheets credentials loaded successfully.")
        else:
            print("Google Sheets credentials secret was empty or failed to retrieve.")
            _creds = None # Ensure _creds is None if not loaded successfully
    except (json.JSONDecodeError, ValueError, RuntimeError) as e:
        print(f"Failed to load/parse Google Sheets credentials (this might be okay if not used for Vertex AI): {e}")
        _creds = None # Ensure _creds is None if loading fails

    # 3. Initialize Vertex AI SDK
    try:
        # We explicitly rely on the Cloud Function's default service account
        # by NOT passing the 'credentials' argument to vertexai.init
        vertexai.init(
            project=PROJECT_ID,
            location=LOCATION,
            #credentials=_creds, # <--- DO NOT PASS _CREDS HERE unless absolutely necessary for Vertex AI itself
        )
        print(f"Vertex AI SDK initialized for project: {PROJECT_ID}, location: {LOCATION} using default service account.")
        
    except Exception as e:
        raise Exception(f"Some Problems in initializing Vertex Ai:Failed to initialize Vertex AI SDK: {e}" )

    # 4. Get the Agent Engine object
    try:
        print('Trying to initialize agent..')
        _remote_agent = agent_engines.get(FQN_AGENT_ID)
        print(f"Successfully retrieved agent: {FQN_AGENT_ID}")
    except google.api_core.exceptions.NotFound:
        # Catch specific NotFound to provide a more specific error message
        raise RuntimeError(
            f"Agent with FQN '{FQN_AGENT_ID}' not found in project '{PROJECT_ID}' location '{LOCATION}'. "
            f"Please verify secret content, agent deployment, and correct project/location."
        )
    except Exception as e:
        # Catch other exceptions during agent retrieval
        raise RuntimeError(f"Failed to get remote agent '{FQN_AGENT_ID}': {e}")
    return "Vertex AI SDK initialized for project"

# --- Global Initialization Block (executed once per cold start) ---
try:
    logging.info('Initializing Vertex ai agent')
    _initialize_vertex_ai_agent()
except Exception as e:
    logging.critical(f"FATAL: Global Vertex AI Agent initialization failed during cold start: {e}")
    _initialization_error = str(e) # Store error to report in the function response

def call_agent(input_text):
    try:
        print(f'Calling agent with {input_text}')
        print(dir(_remote_agent))
        print(_remote_agent.to_dict())
    except Exception as e:
        print(f'Failed to call agent:{str(e)}')



# --- Cloud Function Entry Point ---
def execute_call(request):
    """Responds to any HTTP request, initializing Vertex AI Agent if needed."""
    # First, check if global initialization failed during cold start
    if _initialization_error:
        logging.error(f"Function invoked but global initialization previously failed: {_initialization_error}")
        return f"Error: Global function initialization failed. Details: {_initialization_error}", 500

    # Ensure the agent is initialized. This path will only be taken if _initialize_vertex_ai_agent
    # was successful on cold start. _remote_agent should be populated.
    if _remote_agent is None:
        # This case *should* ideally not be hit if _initialization_error is None,
        # but serves as a failsafe.
        logging.critical("CRITICAL: _remote_agent is None but _initialization_error is also None. Unexpected state.")
        #return "Internal Server Error: Agent not initialized despite no reported init error.", 500

    request_json = request.get_json(silent=True)
    request_args = request.args
    logging.info('Executing Cloud Function with initialized agent.')

    name = 'World I went to the church and met lots of people who greeted me'
    if request_json and 'name' in request_json:
        name = request_json['name']
    elif request_args and 'name' in request_args:
        name = request_args['name']

    # Now, you can actually use _remote_agent here, for example:
    # agent_response = _remote_agent.predict(prompt=f"Hello {name}, what can you do?")
    # response_text = agent_response.candidates[0].text
    call_agent(name)
    # For now, return a confirmation of agent status
    return (
        f'Hello {name}! Nice to see you again. '
        f'Project: {PROJECT_ID}, Location: {LOCATION}. '
        f'Agent FQN: {_remote_agent.name}. '
        f'Agent Location: {_remote_agent.location}'
        f'If creds loaded: {"Yes" if _creds else "No"}.'
    )