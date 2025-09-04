import vertexai
import os
import json
from vertexai import agent_engines
from google.oauth2 import service_account
import google.api_core.exceptions # For more specific error handling

# --- Load Credentials ---
credentials_json_str = os.getenv('GOOGLE_SHEET_CREDENTIALS')
if not credentials_json_str:
    raise ValueError("GOOGLE_SHEET_CREDENTIALS environment variable not set.")
credentials_info = json.loads(credentials_json_str)

creds = service_account.Credentials.from_service_account_info(
    credentials_info
)

# --- Project and Location Initialization ---
PROJECT_ID = os.environ.get('GOOGLE_PROJECT_ID', 'datascience-projects')
LOCATION = "us-central1" # Agent Engine is primarily supported in us-central1

if not PROJECT_ID:
    raise ValueError("GOOGLE_PROJECT_ID environment variable not set.")

vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    credentials=creds,
)

# --- Main Execution Block ---
if __name__ == "__main__":
    FQN_AGENT_ID = os.environ.get('GOOGLE_AGENT_FQN')
    if not FQN_AGENT_ID:
        raise ValueError("GOOGLE_AGENT_FQN environment variable not set. It should be in the format: projects/PROJECT_ID/locations/LOCATION/reasoningEngines/AGENT_ID")

    try:
        # --- Step 1: Get the Agent Object ---
        remote_agent = agent_engines.get(FQN_AGENT_ID)
        print(f"Successfully retrieved agent: {FQN_AGENT_ID}")

        # --- Step 2: Create a Session with the Agent ---
        # This explicitly initiates a new conversation session.
        # It may return a session object or a session ID string.
        # For Agent Engine, 'create_session' is the way to go.
        # The 'user_id' parameter is typically passed here during session creation.
        current_user_id = "my-unique-application-user-id" # A persistent ID for the user
        print(f"\n--- Creating new session for user: {current_user_id} ---")
        session = remote_agent.create_session(user_id=current_user_id)
        # The session object itself might hold the session ID internally,
        # or expose it via a property like session.session_id if you need the string.
        print(f"Session created. Session ID: {dir(session['id'])}")

        # --- Step 3: Send Messages within the Session ---
        # Now, you'll use the 'query' or 'stream_query' method directly on the session object.
        # This automatically links the message to the created session.

        user_query_1 = "Yesterday I went to the church and got applauded by all the people there and I was happy."

        print(f"\n--- Sending First Query within session ---")
        print(f"Query: '{user_query_1}'")

        for event in remote_agent.stream_query(
            user_id=current_user_id,
            session_id=session["id"],
            message=user_query_1,
        ):
            print(f'----- Received {event}')



    # --- Error Handling ---
    except google.api_core.exceptions.NotFound as e:
        print(f"Error: Agent with FQN '{FQN_AGENT_ID}' not found. "
              f"Please verify GOOGLE_AGENT_FQN is correct and the agent is deployed in '{LOCATION}'. Details: {e}")
    except google.api_core.exceptions.PermissionDenied as e:
        print(f"Error: Permission denied. Ensure your service account has the 'Vertex AI User' role "
              f"or other necessary permissions (e.g., 'aiplatform.reasoningEngineInvocations.invoke') on the project. Details: {e}")
    except google.api_core.exceptions.FailedPrecondition as e:
        print(f"Error: Failed precondition. This can happen if the agent's underlying model is not enabled or if there are other setup issues. Details: {e}")
    except Exception as e:
        print(f"An unexpected error occurred: {e}")