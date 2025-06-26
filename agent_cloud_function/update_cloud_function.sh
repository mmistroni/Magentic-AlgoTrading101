#!/bin/bash

# update_function.sh
# This script updates an existing Google Cloud Function.

# --- Configuration Variables ---
# Make sure these match your existing Cloud Function's configuration.

PROJECT_ID="datascience-projects" # Automatically get current project

# Replace with the name of your Cloud Function
FUNCTION_NAME="my_agent_function"

# Replace with the GCP region where your function is deployed (e.g., us-central1, europe-west2)
GCP_REGION="us-central1"

# The runtime for your function (e.g., python310, python311, nodejs18, etc.)
RUNTIME="python311"

# The entry point function name in your main.py (e.g., call_adk_agent)
ENTRY_POINT="execute_call"

# The trigger type (e.g., http, event, pubsub)
TRIGGER_TYPE="http"

# The source directory containing your function code (main.py, requirements.txt, etc.)
# '.' refers to the current directory where you run this script.
SOURCE_DIR="."
FUNCTION_SERVICE_ACCOUNT="myagentfunctionsvc@datascience-projects.iam.gserviceaccount.com"
ALLOW_UNAUTHENTICATED="--allow-unauthenticated" 

# --- Deployment Command ---
echo "--- Starting update for Cloud Function: ${FUNCTION_NAME} in region: ${GCP_REGION} ---"

gcloud functions deploy "${FUNCTION_NAME}" \
    --runtime "${RUNTIME}" \
    --trigger-${TRIGGER_TYPE} \
    --entry-point "${ENTRY_POINT}" \
    --project "datascience-projects" \
    --region "${GCP_REGION}" \
    ${ALLOW_UNAUTHENTICATED} \
    --source="${SOURCE_DIR}" \
    --service-account="${FUNCTION_SERVICE_ACCOUNT}" \
    --verbosity=info # Increase verbosity for more detailed output during deployment

# --- Important Notes ---
echo ""
echo "Deployment command completed. Please check the output above for status."
echo "If you encounter errors, examine the Cloud Build logs in the GCP Console:"
echo "Go to Cloud Functions -> Your Function -> Logs -> Build logs."
echo ""
echo "Remember: The ADK_AGENT_ENDPOINT is now fetched from Secret Manager (adk-agent-url),"
echo "so it's not set directly during this deployment. Ensure your function's"
echo "service account has 'Secret Manager Secret Accessor' role on that secret."

echo "--- Update process finished ---"
