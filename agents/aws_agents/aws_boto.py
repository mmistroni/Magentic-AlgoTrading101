import boto3
import json

# Replace with your actual gateway URL details (extracted from your URL)
GATEWAY_ID = "https://gateway-provision-api-upwyskvdqd.gateway.bedrock-agentcore.us-west-2.amazonaws.com/mcp"
REGION = "us-west-2"

# 1. Initialize the client (It automatically picks up your local AWS credentials and handles SigV4)
client = boto3.client(
    'bedrock-agentcore-runtime',
    region_name=REGION
)

# 2. Define the MCP payload (e.g., to list available tools)
payload = {
    "jsonrpc": "2.0",
    "method": "mcp_listTools",
    "params": {},
    "id": "list-tools-request"
}

# 3. Call the InvokeGateway API
try:
    response = client.invoke_gateway(
        gatewayIdentifier=GATEWAY_ID,
        body=json.dumps(payload).encode('utf-8'),
        contentType='application/json'
    )

    # The response body contains the result from the MCP server
    response_body = json.loads(response['body'].read().decode('utf-8'))
    print("--- Bedrock Gateway Call Successful ---")
    print(json.dumps(response_body, indent=2))

except Exception as e:
    print(f"--- Bedrock Gateway Call Failed ---")
    print(f"Error invoking Gateway: {e}")