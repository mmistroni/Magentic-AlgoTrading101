import os
import json
import requests
import google.auth
from google.auth.transport.requests import Request as AuthRequest
from typing import Dict, Any, Tuple

# --- Configuration ---
CLOUD_RUN_URL = "https://zoo-data-backend-682143946483.europe-west1.run.app"
CREDENTIALS_VAR = "PROGRAMMATIC_AGENT_TOKEN"
DEFAULT_PAYLOAD = {"query": "what animals do you have in your zoo", "location": "europe-west1"}


def get_id_token_credentials(target_audience: str) -> google.auth.credentials.Credentials:
    """
    Loads Google Service Account credentials from a JSON string stored in an
    environment variable and creates ID Token Credentials for Cloud Run invocation.

    Args:
        target_audience: The URL of the Cloud Run service (used as the 'aud' claim).

    Returns:
        A Google Auth Credentials object ready to generate ID tokens.
    """
    key_json = os.environ.get(CREDENTIALS_VAR)
    
    if not key_json:
        raise EnvironmentError(
            f"Authentication failed: The environment variable '{CREDENTIALS_VAR}' is not set."
        )

    try:
        # Load the Service Account JSON content into a dictionary
        service_account_info = json.loads(key_json)
    except json.JSONDecodeError:
        raise ValueError(
            f"Failed to parse JSON content from '{CREDENTIALS_VAR}'. Ensure it's valid JSON."
        )

    # Use the appropriate method to create ID Token Credentials from the dictionary.
    # The 'target_audience' is crucial for authenticating to Cloud Run.
    credentials, _ = google.auth.load_credentials_from_dict(
        service_account_info,
        target_audience=target_audience
    )
    
    return credentials


def invoke_cloud_run_agent(
    url: str,
    payload: Dict[str, Any]
) -> requests.Response:
    """
    Authenticates and makes an authorized POST request to the Cloud Run service.
    
    Args:
        url: The full URL of the Cloud Run service.
        payload: The JSON payload to send to the agent.
        
    Returns:
        The response object from the HTTP request.
    """
    print("🚀 Attempting to authenticate and invoke agent...")
    
    # 1. Get credentials (fetches the ID token internally)
    credentials = get_id_token_credentials(url)
    
    # 2. Refresh the credentials to ensure we have a fresh, valid ID token
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
        response = invoke_cloud_run_agent(
            url=CLOUD_RUN_URL, 
            payload=DEFAULT_PAYLOAD
        )
        
        # Check the HTTP status code
        response.raise_for_status()
        
        # Success output
        print("✅ Agent call successful!")
        print(f"URL: {CLOUD_RUN_URL}")
        print(f"Response Status: {response.status_code}")
        print("\nResponse Body:")
        print(json.dumps(response.json(), indent=4))
        
    except EnvironmentError as e:
        print(f"❌ ERROR: {e}")
        print("\nACTION REQUIRED: Please set the 'PROGRAMMATIC_AGENT_TOKEN' environment variable.")
    except ValueError as e:
        print(f"❌ ERROR: {e}")
    except requests.exceptions.HTTPError as e:
        print(f"❌ HTTP ERROR: Agent call failed with status code {e.response.status_code}")
        if e.response.status_code == 403:
            print("\n**403 Forbidden Error:** Check the following:")
            print("1. The **Cloud Run Invoker** role is granted to the service account.")
            print(f"2. The target audience ({CLOUD_RUN_URL}) is correct.")
        print("Response body:")
        print(e.response.text)
    except Exception as e:
        print(f"❌ An unexpected error occurred: {e}")


if __name__ == "__main__":
    main()