import os
import json
import requests
import google.auth
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2 import service_account 
from typing import Dict, Any

# --- Configuration ---
# CORRECTED: Base URL + the ADK agent's standard streaming endpoint
CLOUD_RUN_URL = "https://stock-agent-service-682143946483.us-central1.run.app/"
# Environment variable storing the service account key JSON content
CREDENTIALS_VAR = "PROGRAMMATIC_AGENT_TOKEN"

# EXAMPLE PAYLOAD: Must match your agent's expected input schema.
# Note that we set "streaming": false to receive a single, complete response.

DEFAULT_PAYLOAD = {
    "app_name": "sttock_agent",  # Check your ADK agent's directory name
    "user_id": "programmatic_user",
    "session_id": "client_session_001",
    "new_message": {
        "role": "user",
        "parts": [{"text": "Run a technical analysis for yesterday stock picks and give me your recommendations"}]
    },
    "streaming": False
}


def get_id_token_credentials(target_audience: str) -> google.auth.credentials.Credentials:
    """
    Loads Service Account credentials and generates an ID Token scoped to the 
    target_audience (Cloud Run URL, including the endpoint path).
    """
    key_json = os.environ.get(CREDENTIALS_VAR)
    
    if not key_json:
        raise EnvironmentError(
            f"Authentication failed: The environment variable '{CREDENTIALS_VAR}' is not set."
        )

    try:
        service_account_info = json.loads(key_json)
    except json.JSONDecodeError:
        raise ValueError(
            f"Failed to parse JSON content from '{CREDENTIALS_VAR}'. Ensure it is valid JSON."
        )

    # Use IDTokenCredentials, passing the full URL (including /run_sse) as the audience
    credentials = service_account.IDTokenCredentials.from_service_account_info(
        info=service_account_info,
        target_audience=target_audience
    )
    print('... Credentials loaded.=,,,,,')
    return credentials


def invoke_cloud_run_agent(
    url: str,
    payload: Dict[str, Any]
) -> requests.Response:
    """
    Authenticates, generates an ID token, and makes the authorized POST request.
    """
    print(f"🚀 Attempting to invoke agent at {url}...")
    
    # We pass the full URL (including /run_sse) as the audience
    credentials = get_id_token_credentials(url) 
    
    auth_req = AuthRequest()
    credentials.refresh(auth_req)
    id_token = credentials.token
    
    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json"
    }

    response = requests.post(url, headers=headers, json=payload)
    
    return response


def main():
    """
    The main execution function for the programmatic client.
    """
    try:
        response = invoke_cloud_run_agent(
            url=f'{CLOUD_RUN_URL}run_sse',  # CORRECTED: Full URL with endpoint
            payload=DEFAULT_PAYLOAD
        )
        
        response.raise_for_status()
        
        print("✅ Agent call successful!")
        print(f"Response Status: {response.status_code}")
        print("\nResponse Body:")
        print(json.dumps(response.json(), indent=4))
        
    except EnvironmentError as e:
        print(f"❌ ERROR: {e}")
        print(f"\nACTION REQUIRED: Set the '{CREDENTIALS_VAR}' environment variable.")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP ERROR: Agent call failed with status code {e.response.status_code}")
        if e.response.status_code == 403:
            print("\n**403 Forbidden Error:** Check the Cloud Run Invoker role on the service account.")
        elif e.response.status_code == 422:
             print("\n**422 Unprocessable Entity:** The payload structure is incorrect. Ensure DEFAULT_PAYLOAD matches the agent's expected schema.")
        print("Response body:")
        print(e.response.text)
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()