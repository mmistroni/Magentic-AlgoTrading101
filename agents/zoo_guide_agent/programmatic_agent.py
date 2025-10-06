import requests
import os
import json
from google.auth import default
from google.auth.transport.requests import Request
from google.auth.exceptions import DefaultCredentialsError
from google.oauth2 import id_token  # <--- NEW/CRITICAL IMPORT for low-level token fetching
# You can remove any previous imports related to AuthorizedSession or IdTokenCredentialsFromCredentials


# --- CONFIGURATION (UPDATE THESE) ---
# Your deployed Cloud Run service URL (no trailing slash)
# You need to authenticate to access the service via gcloud auth
CLOUD_RUN_URL = "https://zoo-tour-guide-682143946483.europe-west1.run.app" 
# 2. VERIFIED APP NAME from --service_name
APP_NAME = "zoo-tour-guide" 
# A unique identifier for the user (can be any string you define)
USER_ID = "programmatic-user-001"
# A unique identifier for this conversation session (e.g., a UUID or a custom string)
SESSION_ID = "session-test-001"

GCP_PROJECT_ID = os.environ.get('GOOGLE_PROJECT_ID') # Use PROJECT_ID as a fallback default


# --- ADK API ENDPOINTS ---
RUN_ENDPOINT = f"{CLOUD_RUN_URL}/run"
# Note: For streaming, you'd use /run_sse

# --- SESSION CONFIGURATION ---
USER_ID = "programmatic-user-001"
SESSION_ID = "session-test-001" 
RUN_ENDPOINT = f"{CLOUD_RUN_URL}/run"


def get_auth_headers(audience: str, project_id: str) -> dict:
    """
    Fetches a raw ID Token using the low-level google.oauth2.id_token
    module, which is highly compatible with user-based Application Default Credentials.
    """
    try:
        # 1. Load generic credentials (relies on gcloud auth and GCLOUD_PROJECT env var)
        credentials, project = default()
        
        # 2. Use the low-level function to fetch the ID Token
        #    It takes the Request object and the audience (Cloud Run URL).
        id_token_value = id_token.fetch_id_token(Request(), audience)
        
        # 3. Check for project context
        if project is None:
             print("[WARNING] Project ID not detected. Ensure 'export GCLOUD_PROJECT=...' was run.")

        print(f"[AUTH] Token acquired. Starts with: {id_token_value[:10]}...") 
        
        return {
            "Authorization": f"Bearer {id_token_value}",
            "Content-Type": "application/json"
        }
    except DefaultCredentialsError as e:
        print("\n--- AUTHENTICATION ERROR: MISSING PROJECT ID / CREDENTIALS ---")
        print("1. Ensure 'gcloud auth application-default login' was successful.")
        print("2. Ensure 'export GCLOUD_PROJECT=YOUR_GCP_PROJECT_ID' was run.")
        raise e
    except Exception as e:
        print(f"[AUTH] General Authentication Error: {e}")
        raise e

def query_agent(message: str) -> str:
    """Sends a query to the public ADK agent's /run endpoint (no authentication needed)."""
    
    # 1. Define the REST payload
    payload = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": SESSION_ID,
        "new_message": {
            "role": "user",
            "parts": [{"text": message}]
        },
        "streaming": False 
    }
    
    # 2. Make the standard POST request
    print(f"\n-> Sending message: '{message}' to {RUN_ENDPOINT}")
    
    # The headers only specify content type, NOT authorization
    headers = {"Content-Type": "application/json"}
    
    try:
        response = requests.post(RUN_ENDPOINT, headers=headers, json=payload)
    except requests.exceptions.RequestException as e:
        return f"Request failed: Could not connect to the endpoint. Check CLOUD_RUN_URL and network access. Error: {e}"

    # 3. Handle the response
    if response.status_code == 200:
        data = response.json()
        
        # Extract the final response text from the list of events
        final_response_event = next((
            event for event in reversed(data.get('events', [])) 
            if event.get('type') == 'FINAL_RESPONSE'
        ), None)

        if final_response_event and 'content' in final_response_event:
            parts = final_response_event['content'].get('parts', [])
            response_text = " ".join(part.get('text', '') for part in parts if 'text' in part)
            return response_text
        
        return "Agent responded (200 OK), but could not parse the final text event."
    
    else:
        return f"Error {response.status_code}: {response.text}"

# --- MAIN EXECUTION ---
def main():
    print("--- Starting Programmatic ADK Agent Interaction (Public Access) ---")
    
    if not CLOUD_RUN_URL:
        print("!!! Please update CLOUD_RUN_URL in the script before running. !!!")
        return
        
    # 1st Message: Conversation start
    response_1 = query_agent("Hello, what can you do?")
    print(f"\n<- Agent Response 1: {response_1}")
    
    # 2nd Message: Follow-up question (uses the same SESSION_ID for memory)
    response_2 = query_agent("Please remember that my favorite animal is the cheetah.")
    print(f"\n<- Agent Response 2: {response_2}")

    # 3rd Message: A new question to test memory
    response_3 = query_agent("What is my favorite animal?")
    print(f"\n<- Agent Response 3: {response_3}")


if __name__ == "__main__":
    main()