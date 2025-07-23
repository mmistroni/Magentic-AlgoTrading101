import requests
import json
import os # Import the os module to access environment variables
import sys

# Removed get_gcloud_identity_token as it's not needed for API Gateway calls with API keys

def call_api_gateway(url: str, params: dict = None, api_key: str = None) -> requests.Response:
    """
    Calls a Google API Gateway endpoint with optional query parameters and API key.

    Args:
        url: The base URL of the API Gateway endpoint (e.g., https://<GATEWAY_URL>/hello).
        params: A dictionary of parameters to be sent as query parameters in the request URL.
        api_key: The API key to be sent in the 'x-api-key' header.

    Returns:
        A requests.Response object containing the server's response.
    """
    headers = {} # No Content-Type header needed for GET requests unless specific API requires it

    if api_key:
        headers['x-api-key'] = api_key # Add the API key to the x-api-key header

    try:
        # Make a GET request to the API Gateway
        # parameters are passed via the 'params' argument for GET requests
        response = requests.get(url, headers=headers, params=params)

        # Raise an exception for HTTP errors (4xx or 5xx)
        response.raise_for_status()

        return response
    except requests.exceptions.RequestException as e:
        print(f"Error calling API Gateway: {e}", file=sys.stderr)
        # Re-raise the exception to allow calling code to handle it
        raise

if __name__ == "__main__":
    # URL for your API Gateway including the /hello endpoint
    api_gateway_url = "https://agent-gateway2-8pdew5pv.uc.gateway.dev/hello"
                       
    # Parameters to be sent as query string for the GET request
    # 'name' is now a query parameter as per your example
    query_params = {"name": "Insert an expense of 33 for beach towels"}# "Can  you list all expenses for user marco?"}

    # Get the API key from the environment variable
    # The environment variable is named X_API_KEY as per your request
    api_key_from_env = os.getenv("X_API_KEY")

    if api_key_from_env:
        print("Calling API Gateway with query parameters and API key...")
        try:
            response = call_api_gateway(api_gateway_url, params=query_params, api_key=api_key_from_env)
            print(f"Status Code: {response.status_code}")
            print(f"Response Body: {response.text}")

            # Attempt to parse as JSON if the response content type indicates JSON
            # or if it looks like JSON
            if 'application/json' in response.headers.get('Content-Type', ''):
                try:
                    json_response = response.json()
                    print(f"Parsed JSON Response: {json_response}")
                except json.JSONDecodeError:
                    print("Response is not valid JSON.", file=sys.stderr)
            else:
                print("Response is not JSON type.", file=sys.stderr)


        except Exception as e:
            print(f"Failed to call API Gateway: {e}", file=sys.stderr)
    else:
        print("Error: 'X_API_KEY' environment variable not found.", file=sys.stderr)
        print("Please set the X_API_KEY environment variable before running this script.", file=sys.stderr)
