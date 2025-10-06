import os
import requests
import os
import json
from google.auth import default
from google.auth.transport.requests import Request
from google.auth.exceptions import DefaultCredentialsError

# --- CONFIGURATION (UPDATE THESE) ---
# Your deployed Cloud Run service URL (no trailing slash)
# You need to authenticate to access the service via gcloud auth
CLOUD_RUN_URL = "https://zoo-tour-guide-682143946483.europe-west1.run.app"
# The name of your agent application (defaults to your directory name, but "zoo-tour-guide" is a safe bet here)
APP_NAME = "zoo-tour-guide" 
# A unique identifier for the user (can be any string you define)
USER_ID = "programmatic-user-001"
# A unique identifier for this conversation session (e.g., a UUID or a custom string)
SESSION_ID = "session-test-001"

GCP_PROJECT_ID = os.environ['GOOGLE_CLOUD_PROJECT'] # Use PROJECT_ID as a fallback default


# --- ADK API ENDPOINTS ---
RUN_ENDPOINT = f"{CLOUD_RUN_URL}/run"
# Note: For streaming, you'd use /run_sse

# --- SESSION CONFIGURATION ---
USER_ID = "programmatic-user-001"
SESSION_ID = "session-test-001" 
RUN_ENDPOINT = f"{CLOUD_RUN_URL}/run"

def get_auth_headers(audience: str, project_id: str) -> dict:
    """Generates an authenticated header for the Cloud Run service using an ID Token."""
    try:
        # Get credentials, explicitly setting the project for the quota
        credentials, project = default(project=project_id)
        
        # Refresh credentials if necessary
        if credentials and not credentials.valid:
             credentials.refresh(Request())
        
        # Fetch the ID Token using the Cloud Run URL as the audience
        auth_request = Request()
        credentials.fetch_id_token(auth_request, audience)
        id_token = credentials.token
        
        print(f"[AUTH] Token acquired. Starts with: {id_token[:10]}...") 
        
        return {
            "Authorization": f"Bearer {id_token}",
            "Content-Type": "application/json"
        }
    except DefaultCredentialsError as e:
        print("\n--- AUTHENTICATION ERROR: MISSING PROJECT ID / CREDENTIALS ---")
        print("1. Ensure 'gcloud auth application-default login' was successful.")
        print("2. Set GCP_PROJECT_ID correctly in the script.")
        raise e
    except Exception as e:
        print(f"[AUTH] General Authentication Error: {e}")
        raise e

def query_agent(message: str, headers: dict) -> str:
    """Sends a query to the ADK agent's /run endpoint (non-streaming)."""
    
    # 1. Define the REST payload according to ADK's /run schema
    payload = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": SESSION_ID,
        "new_message": {
            "role": "user",
            "parts": [{"text": message}]
        },
        "streaming": False # Explicitly request non-streaming response
    }
    
    # 2. Make the authenticated POST request
    print(f"\n-> Sending message: '{message}' to {RUN_ENDPOINT}")
    
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
    
    elif response.status_code == 403:
        return f"Error {response.status_code} (Forbidden): Authentication failed. Ensure the authenticated user/service account has the Cloud Run Invoker role on the service."
    else:
        return f"Error {response.status_code}: {response.text}"

# --- MAIN EXECUTION ---
def main():
    print("--- Starting Programmatic ADK Agent Interaction ---")
    
    if not CLOUD_RUN_URL or not GCP_PROJECT_ID:
        print("!!! Please update CLOUD_RUN_URL and GCP_PROJECT_ID in the script before running. !!!")
        return
        
    # Authenticate once before sending messages
    try:
        auth_headers = get_auth_headers(CLOUD_RUN_URL, GCP_PROJECT_ID)
    except Exception as e:
        # Authentication error already printed inside get_auth_headers
        raise e

    # 1st Message: Conversation start
    response_1 = query_agent("Hello, what can you do?", auth_headers)
    print(f"<- Agent Response 1: {response_1}")
    
    # 2nd Message: Follow-up question (same SESSION_ID for memory)
    response_2 = query_agent("Please remember that my favorite animal is the cheetah.", auth_headers)
    print(f"<- Agent Response 2: {response_2}")

    # 3rd Message: Test memory
    response_3 = query_agent("What is my favorite animal?", auth_headers)
    print(f"<- Agent Response 3: {response_3}")


if __name__ == "__main__":
    # Temporarily set the environment variable as a fallback, 
    # though we pass it explicitly in the function call for robustness.
    os.environ['GCLOUD_PROJECT'] = GCP_PROJECT_ID
    print(f"{os.environ['GCLOUD_PROJECT']}|")
    main()