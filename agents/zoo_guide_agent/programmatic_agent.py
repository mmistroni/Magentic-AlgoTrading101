import os
import json
import requests
import google.auth
from google.auth.transport.requests import Request as AuthRequest
from google.oauth2 import service_account 
from typing import Dict, Any

# --- Configuration ---
# Your specific Cloud Run service URL
CLOUD_RUN_URL = "https://zoo-data-backend-682143946483.europe-west1.run.app"
# Environment variable storing the service account key JSON content
CREDENTIALS_VAR = "PROGRAMMATIC_AGENT_TOKEN"
# Example payload your agent expects
DEFAULT_PAYLOAD = {"action": "get_inventory", "item_type": "lion"}


def get_id_token_credentials(target_audience: str) -> google.auth.credentials.Credentials:
    """
    Loads Service Account credentials from the PROGRAMMATIC_AGENT_TOKEN environment 
    variable and configures them for ID Token generation with the specified audience.
    """
    print(f"🔑 Loading service account credentials...{os.environ[CREDENTIALS_VAR]}")
    key_json = os.environ.get(CREDENTIALS_VAR)
    
    if not key_json:
        raise EnvironmentError(
            f"Authentication failed: The environment variable '{CREDENTIALS_VAR}' is not set."
        )

    try:
        service_account_info = json.loads(key_json)
    except json.JSONDecodeError:
        raise ValueError(
            f"Failed to parse JSON content from '{CREDENTIALS_VAR}'. Ensure it is valid, unescaped JSON."
        )

    # Use the IDTokenCredentials class which correctly accepts the target_audience 
    # to scope the token for Cloud Run.
    credentials = service_account.IDTokenCredentials.from_service_account_info(
        info=service_account_info,
        target_audience=target_audience
    )
    
    return credentials


def invoke_cloud_run_agent(
    url: str,
    payload: Dict[str, Any]
) -> requests.Response:
    """
    Handles authentication, token fetching, and makes the authorized POST request.
    """
    print(f"🚀 Attempting to invoke agent at {url}...")
    
    # 1. Get credentials, scoped to the Cloud Run URL
    credentials = get_id_token_credentials(url) 
    
    # 2. Use the credentials object to generate a fresh ID token
    auth_req = AuthRequest()
    credentials.refresh(auth_req)
    id_token = credentials.token
    
    # 3. Prepare the authorized request headers
    headers = {
        "Authorization": f"Bearer {id_token}",
        "Content-Type": "application/json"
    }

    # 4. Make the secure POST request
    response = requests.post(url, headers=headers, json=payload)
    
    return response


def main():
    """
    The main execution function for the programmatic client.
    """
    try:
        # Quick check for required libraries
        import google.auth.transport.requests 
        import requests 
        
        response = invoke_cloud_run_agent(
            url=f'{CLOUD_RUN_URL}/run', 
            payload=DEFAULT_PAYLOAD
        )
        
        # Check the HTTP status code and raise an exception if it's 4xx or 5xx
        response.raise_for_status()
        
        # Success output
        print("✅ Agent call successful!")
        print(f"Response Status: {response.status_code}")
        print("\nResponse Body:")
        print(json.dumps(response.json(), indent=4))
        
    except EnvironmentError as e:
        print(f"❌ ERROR: {e}")
        print(f"\nACTION REQUIRED: Set the '{CREDENTIALS_VAR}' environment variable with the full JSON key content.")
    except ValueError as e:
        print(f"❌ ERROR: {e}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP ERROR: Agent call failed with status code {e.response.status_code}")
        if e.response.status_code == 403:
            print("\n**403 Forbidden Error:** Check the following:")
            print("1. The **Cloud Run Invoker** role is granted to the service account.")
            print(f"2. The 'target_audience' ({CLOUD_RUN_URL}) is correct.")
        print("Response body:")
        print(e.response.text)
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}. Please ensure required libraries are installed.")


if __name__ == "__main__":
    main()