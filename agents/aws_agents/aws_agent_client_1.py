import requests
import json
import base64
import os



# --- USER-PROVIDED CREDENTIALS (Keep these) ---
CLIENT_ID = os.environ['AWS_CLIENT_ID']
CLIENT_SECRET = os.environ['AWS_CLIENT_SECRET']
TOKEN_URL = os.environ['TOKEN_URL']

# --- FIX: Configuration for Bedrock Gateway Authentication ---
# 1. This must be the exact Identifier of the Resource Server in your Cognito User Pool.
#    (We extracted this from your hardcoded scope.)
RESOURCE_SERVER_ID = "default-m2m-resource-server-r5rfec"

# 2. This is the exact scope the Bedrock Agent Gateway requires to list tools.
REQUIRED_SCOPE = f"{RESOURCE_SERVER_ID}/read"
# -------------------------------------------------------------


def decode_jwt_payload(token: str) -> dict:
    """Decodes the payload section of a JWT token for inspection."""
    try:
        # JWT format is header.payload.signature
        _, payload_encoded, _ = token.split('.')
        # Pad payload for correct base64 decoding (standard practice for JWT)
        payload_decoded = base64.urlsafe_b64decode(payload_encoded + '==')
        return json.loads(payload_decoded)
    except Exception as e:
        # If decoding fails, return an error message
        return {"error": f"Could not decode token payload: {e}"}


def fetch_access_token(client_id: str, client_secret: str, token_url: str, scope: str) -> str:
    """
    Exchanges the client ID and secret for an access token using the 
    Client Credentials Grant Flow, requesting the specified scope.
    """
    print(f"Attempting to fetch token with scope: {scope}")
    
    try:
        # The 'scope' parameter is crucial for M2M authentication
        data = (
            "grant_type=client_credentials"
            f"&client_id={client_id}"
            f"&client_secret={client_secret}"
            f"&scope={scope}" 
        )
        
        response = requests.post(
            token_url,
            data=data,
            headers={'Content-Type': 'application/x-www-form-urlencoded'}
        )
        
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        
        token_data = response.json()
        
        if 'access_token' in token_data:
            token = token_data['access_token']
            
            # Debugging step: Print payload to confirm the scope is in the token
            payload = decode_jwt_payload(token)
            print("\n--- Decoded Token Payload (Check 'scope' and 'aud' keys) ---")
            print(json.dumps(payload, indent=2))
            print("-----------------------------------------------------------\n")
            
            return token
        else:
            print("Error: 'access_token' not found in response.")
            print(json.dumps(token_data, indent=2))
            return None

    except requests.exceptions.RequestException as e:
        print(f"Error fetching access token from Cognito: {e}")
        return None

def list_tools(gateway_url: str, access_token: str) -> dict:
    """
    Calls the Bedrock Agent Core Gateway to list available tools.
    """
    if not access_token:
        return {"error": "Access token is missing, cannot call Gateway."}

    print(f"Calling Bedrock Gateway at {gateway_url}...")
    
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {access_token}"
    }

    payload = {
        "jsonrpc": "2.0",
        "id": "list-tools-request",
        "method": "tools/list"
    }

    try:
        response = requests.post(gateway_url, headers=headers, json=payload)
        response.raise_for_status() # Raise an HTTPError for bad responses (4xx or 5xx)
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"\n--- Bedrock Gateway Call Failed ---")
        print(f"Error calling Gateway: {e}")
        if e.response is not None:
             print(f"Status Code: {e.response.status_code}")
             print(f"Response Body: {e.response.text}")
        print("-----------------------------------")
        
        # Return the specific error object for the user to see
        return {
            "jsonrpc": "2.0",
            "id": "list-tools-request",
            "error": {
                "code": -32001,
                "message": f"Authentication error - Invalid credentials (See console log for details: {e})"
            }
        }


# Example usage
gateway_url = "https://gateway-provision-api-upwyskvdqd.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp"

# 1. Fetch the token (now requesting the correct scope)
access_token = fetch_access_token(CLIENT_ID, CLIENT_SECRET, TOKEN_URL, REQUIRED_SCOPE)

if access_token:
    # 2. Use the token to call the Gateway
    tools = list_tools(gateway_url, access_token)
    print("\n--- Final Gateway Response ---")
    print(json.dumps(tools, indent=2))
