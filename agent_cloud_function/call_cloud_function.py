import requests
import json
import subprocess
import sys

def get_gcloud_identity_token() -> str | None:
    """
    Obtains the gcloud identity token using the subprocess module.
    This assumes `gcloud` CLI is installed and configured on the system.

    Returns:
        The identity token string if successful, None otherwise.
    """
    try:
        # Execute the gcloud command to print the identity token
        # use sys.executable for cross-platform compatibility if running in a virtual environment
        command = ["gcloud", "auth", "print-identity-token"]
        process = subprocess.run(command, capture_output=True, text=True, check=True)
        return process.stdout.strip()
    except subprocess.CalledProcessError as e:
        print(f"Error getting gcloud identity token: {e}", file=sys.stderr)
        print(f"Stderr: {e.stderr}", file=sys.stderr)
        return None
    except FileNotFoundError:
        print("Error: 'gcloud' command not found. Please ensure gcloud CLI is installed and in your PATH.", file=sys.stderr)
        return None

def call_cloud_function(url: str, data: dict = None, auth_token: str = None) -> requests.Response:
    """
    Calls a Google Cloud Function with optional JSON payload and authorization token.

    Args:
        url: The URL of the Google Cloud Function.
        data: A dictionary to be sent as a JSON payload in the request body.
        auth_token: An optional authentication token (e.g., gcloud identity token).

    Returns:
        A requests.Response object containing the server's response.
    """
    headers = {'Content-Type': 'application/json'}

    if auth_token:
        headers['Authorization'] = f'bearer {auth_token}' # Add Authorization header

    try:
        # Make a POST request to the Cloud Function
        if data:
            response = requests.post(url, headers=headers, data=json.dumps(data))
        else:
            response = requests.post(url, headers=headers)

        # Raise an exception for HTTP errors (4xx or 5xx)
        response.raise_for_status()

        return response
    except requests.exceptions.RequestException as e:
        print(f"Error calling Cloud Function: {e}", file=sys.stderr)
        # Re-raise the exception to allow calling code to handle it
        raise

if __name__ == "__main__":
    function_url = "https://my-agent-function-682143946483.us-central1.run.app"
    payload = {"name": "Can you list all expenses for user marco"}#

    # Get the gcloud identity token
    token = get_gcloud_identity_token()

    if token:
        print("Calling Cloud Function with payload and authentication...")
        try:
            response = call_cloud_function(function_url, data=payload, auth_token=token)
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")

            # Attempt to parse as JSON if it looks like JSON
            try:
                json_response = response.json()
                print(f"Parsed JSON Response: {json_response}")
            except json.JSONDecodeError:
                print("Response is not valid JSON.", file=sys.stderr)

        except Exception as e:
            print(f"Failed to call function with authentication: {e}", file=sys.stderr)
    else:
        print("Could not obtain gcloud identity token. Cannot call authenticated function.", file=sys.stderr)
        print("Please ensure you are logged into gcloud and your credentials are set up correctly.", file=sys.stderr)
