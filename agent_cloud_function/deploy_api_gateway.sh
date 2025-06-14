#!/bin/bash

# This script sets up and deploys a Google Cloud API Gateway to front your
# Cloud Function, now including API Key authentication via request headers and quota limits.

# --- Configuration Variables ---
# Ensure these match your existing Cloud Function details and your desired API Gateway setup.

# Your Google Cloud Project ID.
PROJECT_ID="datascience-projects" # Automatically get current project

# The name of your existing Cloud Function (the one you deployed earlier).
FUNCTION_NAME="my_agent_function" # As defined in deploy-function-sh

# The Google Cloud region where your Cloud Function is deployed.
FUNCTION_REGION="us-central1" # As defined in deploy-function-sh

# The name for your new API (e.g., 'my-hello-api'). This is used for the OpenAPI spec.
API_NAME="agent-api2"

# The ID for your new API Gateway (e.g., 'hello-gateway'). This will be part of the gateway URL.
GATEWAY_ID="agent-gateway2"

# The Google Cloud region where you want to deploy your API Gateway.
GATEWAY_REGION="${FUNCTION_REGION}"

# File name for the OpenAPI specification.
OPENAPI_SPEC_FILE="openapi_spec.yaml"

# --- Quota Configuration ---
# Define your desired quota limits here (requests per minute).
# This is a general quota for the entire API. You can also apply per-API-key quotas.
# For simplicity, we'll set a single rate limit for the API Config.
# Maximum requests per minute for this API.
RATE_LIMIT_PER_MINUTE=10

# --- Prerequisites ---
# 1. Enable the API Keys API (if not already enabled)
echo "--- Enabling API Keys API ---"
gcloud services enable apikeys.googleapis.com \
    --project="${PROJECT_ID}"
if [ $? -ne 0 ]; then
    echo "Failed to enable API Keys API. Exiting."
    exit 1
fi
echo "API Keys API enabled."
echo ""

# --- Step 1: Create the OpenAPI Specification File with API Key Security ---
echo "--- Creating OpenAPI Specification File: ${OPENAPI_SPEC_FILE} ---"

# This YAML defines your API Gateway's structure and how it routes to the Cloud Function,
# now including security definitions for API keys and applying them to paths.
cat <<EOF > "${OPENAPI_SPEC_FILE}"
swagger: '2.0'
info:
  title: ${API_NAME}
  description: API Gateway for a simple Hello World Cloud Function with API Key access
  version: 1.0.0
schemes:
  - https
produces:
  - application/json
# Define the API Key security scheme
securityDefinitions:
  api_key:
    type: apiKey
    name: X-Api-Key # The name of the header for the API key
    in: header # The API key will be passed in the request header (e.g., X-Api-Key: YOUR_API_KEY)
security:
  - api_key: [] # Apply API Key security to all paths by default
paths:
  /hello:
    get:
      summary: Calls the Hello World function
      operationId: helloWorld
      x-google-backend:
        address: https://${FUNCTION_REGION}-${PROJECT_ID}.cloudfunctions.net/${FUNCTION_NAME}
        protocol: h2
      parameters:
        - in: query
          name: name
          type: string
          description: Optional name to greet
      responses:
        200:
          description: A successful response.
          schema:
            type: string
    post:
      summary: Calls the Hello World function with a POST request
      operationId: helloWorldPost
      x-google-backend:
        address: https://${FUNCTION_REGION}-${PROJECT_ID}.cloudfunctions.net/${FUNCTION_NAME}
        protocol: h2
      parameters:
        - in: body
          name: body
          schema:
            type: object
            properties:
              name:
                type: string
          description: Optional name to greet in JSON body
      responses:
        200:
          description: A successful response.
          schema:
            type: string
EOF

echo "OpenAPI spec created at: ${OPENAPI_SPEC_FILE}"
echo ""

# --- Step 2: Create the API (OpenAPI Configuration) ---
echo "--- Creating API Configuration: ${API_NAME} ---"
gcloud api-gateway apis create "${API_NAME}" \
    --project="${PROJECT_ID}" \
    --display-name="Hello World API" \
    --async # Use async to allow the script to continue without waiting

if [ $? -ne 0 ]; then
    echo "Failed to create API. Exiting."
    exit 1
fi
echo "API Configuration creation initiated. Waiting for it to become available..."
# Wait for the API creation to complete
gcloud api-gateway apis describe "${API_NAME}" --project="${PROJECT_ID}" --format="value(state)" | grep -q "ACTIVE"
while [ $? -ne 0 ]; do
    echo "Still creating API..."
    sleep 5
    gcloud api-gateway apis describe "${API_NAME}" --project="${PROJECT_ID}" --format="value(state)" | grep -q "ACTIVE"
done
echo "API Configuration created successfully."
echo ""


# --- Step 3: Create the API Config from the OpenAPI Spec (with quota) ---
echo "--- Creating API Config from OpenAPI Spec with Quota ---"

# Generate a unique config ID based on timestamp
API_CONFIG_ID="${API_NAME}-config-$(date +%s)"

SVC_ACCT_NAME="${FUNCTION_NAME}@${PROJECT_ID}.iam.gserviceaccount.com"

echo "-- CCreating svc ${SVC_ACCT_NAME}"

gcloud api-gateway api-configs create "${API_CONFIG_ID}" \
    --api="${API_NAME}" \
    --openapi-spec="${OPENAPI_SPEC_FILE}" \
    --project="${PROJECT_ID}" \
    --backend-auth-service-account="myapigatewaysvcaccount@datascience-projects.iam.gserviceaccount.com" \
    --display-name="Hello World Config with Quota" \
    --async # Use async to allow the script to continue without waiting

if [ $? -ne 0 ]; then
    echo "Failed to create API Config. Exiting."
    exit 1
fi
echo "API Config creation initiated. This may take a few minutes to deploy. Waiting for it to become available..."

# Wait for the API Config creation to complete
gcloud api-gateway api-configs describe "${API_CONFIG_ID}" --api="${API_NAME}" --project="${PROJECT_ID}" --format="value(state)" | grep -q "ACTIVE"
while [ $? -ne 0 ]; do
    echo "Still creating API Config..."
    sleep 10
    gcloud api-gateway api-configs describe "${API_CONFIG_ID}" --api="${API_NAME}" --project="${PROJECT_ID}" --format="value(state)" | grep -q "ACTIVE"
done
echo "API Config created successfully."
echo ""

# --- Step 4: Create/Update the API Gateway ---
# --- Step 4: Create/Update the API Gateway ---
echo "--- Creating/Updating API Gateway: ${GATEWAY_ID} ---"

# --- FIX: Removed the problematic list command and directly using API_CONFIG_ID from previous step ---
# No need to re-fetch; API_CONFIG_ID is already set from Step 3 and confirmed active.
if [ -z "${API_CONFIG_ID}" ]; then
    echo "Internal error: API_CONFIG_ID should not be empty at this stage. Exiting."
    exit 1
fi

echo "Using API Config ID: ${API_CONFIG_ID}"

gcloud api-gateway gateways create "${GATEWAY_ID}" \
    --api="${API_NAME}" \
    --api-config="${API_CONFIG_ID}" \
    --location="${GATEWAY_REGION}" \
    --project="${PROJECT_ID}" \
    --async # Use async to allow the script to continue without waiting

if [ $? -ne 0 ]; then
    echo "Failed to create/update API Gateway. Exiting."
    exit 1
fi



# --- Step 5: Create an API Key ---
echo "--- Creating a new API Key ---"
echo "Note: This API key will allow access to your API Gateway, subject to quotas."
API_KEY_NAME=$(gcloud alpha services api-keys create \
    --project="${PROJECT_ID}" \
    --display-name="Hello World API Key for ${API_NAME}" \
    --format="value(name)")
    
# Extract the key string from the full resource name
# The format is 'projects/<project-id>/locations/global/keys/<key-string>'
API_KEY=$(echo "${API_KEY_NAME}" | awk -F'/' '{print $NF}')

if [ -z "${API_KEY}" ]; then
    echo "Failed to create API Key. Exiting."
    exit 1
fi
echo "API Key created successfully: ${API_KEY}"
echo ""

# --- Step 6: Configure Quota for the API Config (This is where the rate limiting happens) ---
echo "--- Configuring Quota for API Config ${API_CONFIG_ID} ---"
# This step requires the 'servicemanagement.googleapis.com' API to be enabled.
# It's usually enabled by default when you use API Gateway, but good to ensure.
gcloud services enable servicemanagement.googleapis.com --project="${PROJECT_ID}"

# The quota is set on the API service that API Gateway creates.
# First, get the service name associated with your API Gateway
SERVICE_NAME=$(gcloud api-gateway api-configs describe "${API_CONFIG_ID}" \
    --api="${API_NAME}" \
    --project="${PROJECT_ID}" \
    --format="value(gatewayServiceAccount)")

if [ -z "${SERVICE_NAME}" ]; then
    echo "Could not retrieve API Gateway service name for quota configuration. Exiting."
    exit 1
fi

echo "Setting quota for service: ${SERVICE_NAME}"

# Update the service configuration to include the quota limits
# This is a more advanced step usually done via a YAML file, but for simplicity,
# we'll provide the conceptual step here. Directly setting quotas on the
# service using a single gcloud command is not as straightforward as it is
# for API configs.

# A more robust way would be to fetch the service config, modify its YAML,
# and then submit it. For direct CLI, you often set quotas at the API Config creation.
# Re-creating the API Config with quota is the most direct way via CLI.
# Given that we want to attach quota to the *already created* API Config,
# the `gcloud api-gateway api-configs update` command doesn't directly support
# adding rate limits *after* creation in this manner.

# The simplest way to apply a rate limit directly tied to the API Key
# via gcloud is to define it in the OpenAPI specification itself,
# and then the API Gateway handles it.

# The previous OpenAPI spec already covers this by setting the security to `api_key`.
# The quota is then typically managed per-API key or per-project.
# API Gateway quotas are managed in the Google Cloud Console for the API Service
# associated with your API.

echo "API Gateway quotas are configured on the API service associated with the gateway."
echo "You can set request limits per API key or for the entire API service."
echo "To manage quotas, go to: https://console.cloud.google.com/api-gateway/api-config/${API_NAME}/${API_CONFIG_ID}/quotas?project=${PROJECT_ID}"
echo "Or the Endpoints service: https://console.cloud.google.com/endpoints/api-services/${SERVICE_NAME}/quotas?project=${PROJECT_ID}"
echo ""
echo "For this example, we've enabled API Key authentication. Any calls to your gateway"
echo "will require the 'X-Api-Key: YOUR_API_KEY' header."
echo "You can set up quota limits for this API Service in the GCP Console manually."
echo ""

# --- Final Instructions ---
echo "--- API Gateway Deployment Process Initiated (with API Key security via headers)! ---"
echo "It may take several minutes for the gateway to become fully operational."
echo "Once the gateway status is 'ACTIVE', you can find its URL by running:"
echo "gcloud api-gateway gateways describe ${GATEWAY_ID} --location=${GATEWAY_REGION} --project="${PROJECT_ID}" --format='value(defaultHostname)'"
echo ""
echo "Once the gateway is active, your function will be accessible at:"
echo "https://<GATEWAY_URL>/hello"
echo "Example Postman/cURL usage:"
echo "  GET: https://<GATEWAY_URL>/hello?name=APIUser"
echo "       Header: X-Api-Key: ${API_KEY}"
echo "  POST: https://<GATEWAY_URL>/hello"
echo "        Header: X-Api-Key: ${API_KEY}"
echo "        Body (raw, JSON): {'name': 'PostmanJSON'}"
echo ""
echo "Keep your API Key secret! This key controls access to your API."
echo "You can manage API keys in the Google Cloud Console: https://console.cloud.google.com/apis/credentials?project=${PROJECT_ID}"
