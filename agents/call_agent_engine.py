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
        print(f"Session created. Session ID: {dir(session)}")

        # --- Step 3: Send Messages within the Session ---
        # Now, you'll use the 'query' or 'stream_query' method directly on the session object.
        # This automatically links the message to the created session.

        user_query_1 = "Yesterday I went to the church and got applauded by all the people there and I was happy."

        print(f"\n--- Sending First Query within session ---")
        print(f"Query: '{user_query_1}'")

        stream_response_1 = session.stream_query(
            message=user_query_1,
            # user_id is typically not needed again here if it was passed in create_session
            # enable_tracing=True # Uncomment for verbose debugging
        )

        # --- Step 4: Process the Streaming Response ---
        full_response_text_1 = ""
        for event in stream_response_1:
            if "messages" in event:
                for message_content in event["messages"]:
                    if "text" in message_content:
                        text_chunk = message_content["text"]
                        full_response_text_1 += text_chunk
                        print(f"Agent Text Chunk: {text_chunk}", end='', flush=True)
            elif "output" in event:
                output_data = event["output"]
                if "text" in output_data:
                    final_text = output_data["text"]
                    full_response_text_1 += final_text
                    print(f"\nFinal Agent Output Text (from 'output' key): {final_text}")
                else:
                    print(f"\nAgent Final Structured Output: {json.dumps(output_data, indent=2)}")
            elif "actions" in event:
                print(f"\n--- Agent Actions Event: {json.dumps(event['actions'], indent=2)} ---")
            elif "debug" in event:
                print(f"\n--- Agent Debug Event: {json.dumps(event['debug'], indent=2)} ---")
            else:
                print(f"\n--- Unhandled Event Type: {json.dumps(event, indent=2)} ---")

        print(f"\n--- Full First Conversation Response: {full_response_text_1} ---")


        # --- Follow-up message within the SAME session ---
        # No need to pass session_id explicitly; it's handled by the 'session' object.
        user_query_2 = "What did you think of that experience?"

        print(f"\n--- Sending Follow-up Query within session ---")
        print(f"Query: '{user_query_2}'")

        stream_response_2 = session.stream_query(
            message=user_query_2,
            # enable_tracing=True
        )

        full_response_text_2 = ""
        for event in stream_response_2:
            if "messages" in event:
                for message_content in event["messages"]:
                    if "text" in message_content:
                        text_chunk = message_content["text"]
                        full_response_text_2 += text_chunk
                        print(f"Agent Text Chunk: {text_chunk}", end='', flush=True)
            # Add other event type handling if needed for follow-up
        print(f"\n--- Full Follow-up Conversation Response: {full_response_text_2} ---")


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