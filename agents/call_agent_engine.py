import vertexai
import os
import uuid # You'll need this for generating session IDs
import json
from vertexai import agent_engines
from google.oauth2 import service_account

# --- Load Credentials (Your existing code) ---
credentials_json_str = os.getenv('GOOGLE_SHEET_CREDENTIALS')
if not credentials_json_str:
    raise ValueError("GOOGLE_SHEET_CREDENTIALS environment variable not set.")

credentials_info = json.loads(credentials_json_str)

creds = service_account.Credentials.from_service_account_info(
        credentials_info
    )

# --- Project and Location Initialization (Your existing code) ---
PROJECT_ID = os.environ.get('GOOGLE_PROJECT_ID')
LOCATION = "us-central1" # Agent Engine is primarily supported in us-central1

# Ensure PROJECT_ID is set
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
        raise ValueError("GOOGLE_AGENT_FQN environment variable not set.")
    
    try:
        remote_agent = agent_engines.get(FQN_AGENT_ID)

        # --- IMPORTANT CHANGES HERE ---
        # 1. Use 'message' keyword for the user's input.
        # 2. Provide a 'user_id' (required by AdkApp.stream_query).
        # 3. Provide a 'session_id' to maintain conversation context.
        #    Generate a new one for each new conversation, reuse for follow-ups.

        user_query = "Yesterday I went to the church and got applauded by all the people there and I was happy."
        
        # We need to create a session first
        
        current_session_id = str(uuid.uuid4()) # Generate a unique session ID for this conversation
        current_user_id = "my-unique-user-id-123" # A unique ID for the user

        print(f"\n--- Sending Query: '{user_query}' ---")
        print(f"Session ID: {current_session_id}, User ID: {current_user_id}")

        stream_response = remote_agent.stream_query(
            session_id=current_session_id, # Key for conversation memory
            message=user_query,           # The correct parameter for user input
            user_id=current_user_id       # Required user identifier
        )

        # --- Processing the Stream (Your existing logic, slightly enhanced) ---
        for event in stream_response:
            print(f"Message is:{event}")
            
        
    except Exception as e:
        print(f"An error occurred during agent invocation: {e}")
        # Add more specific error handling here if you know what kind of exceptions
        # your agent or the SDK might throw (e.g., authentication, resource not found)