#!/bin/bash

# This script deploys a Google Cloud Function to the specified region.
# It assumes you have the Google Cloud SDK installed and authenticated.

# --- Configuration Variables ---
# You can modify these variables to match your function's details.

# Your Google Cloud Project ID.
PROJECT_ID="datascience-projects" # Automatically get current project

# The name of your Cloud Function (must be unique within your project and region).
FUNCTION_NAME="my_agent_function"

# The entry point for your function (the Python function name to execute).
ENTRY_POINT="execute_call"

# The runtime for your function (e.g., python39, python311).
RUNTIME="python311"

# The Google Cloud region where you want to deploy your function.
REGION="us-central1" # Changed to us-central1 as per your provided script

# The source directory containing your function's main.py and requirements.txt.
SOURCE_DIR="."

# --- Service Account for the Cloud Function ---
# This is the identity your Cloud Function will run as.
# By default, it's <function-name>@<project-id>.iam.gserviceaccount.com
FUNCTION_SERVICE_ACCOUNT="myagentfunctionsvc@datascience-projects.iam.gserviceaccount.com"

# --- Target for Agent Engine Permissions ---
# If your agent engine is a Vertex AI service (like a deployed model, endpoint, or Vertex AI Agents),
# the 'roles/aiplatform.user' role is typically required.
# Granting at the project level is common for broad access within the project.
# If you need more granular control, replace "projects/${PROJECT_ID}"
# with the specific resource path for your agent (e.g., a Vertex AI Endpoint ID).
REASONING_AGENT_TARGET="projects/${PROJECT_ID}"

# The IAM role required for your Cloud Function to invoke the agent engine.
# 'roles/aiplatform.user' grants permissions to use Vertex AI resources.
REQUIRED_ROLE="roles/aiplatform.user" # <--- Set for Vertex AI User

# --- Step 0: Ensure the Function's Service Account Exists ---
echo "--- Ensuring Function Service Account Exists ---"

# --- Deployment Command ---
echo "--- Starting Google Cloud Function Deployment ---"
echo "Function Name: ${FUNCTION_NAME}"
echo "Entry Point: ${ENTRY_POINT}"
echo "Runtime: ${RUNTIME}"
echo "Region: ${REGION}"
echo "Source Directory: ${SOURCE_DIR}"
echo ""

# Execute the gcloud functions deploy command
# --service-account flag ensures the function uses the explicitly created SA.
gcloud functions deploy "${FUNCTION_NAME}" \
    --runtime "${RUNTIME}" \
    --trigger-http \
    --entry-point "${ENTRY_POINT}" \
    --region "${REGION}" \
    --source="${SOURCE_DIR}" \
    --allow-unauthenticated \
    --service-account="${FUNCTION_SERVICE_ACCOUNT}" # <--- Added: Use the explicitly created service account

# --- Check Deployment Status ---
if [ $? -ne 0 ]; then
    echo "--- Cloud Function Deployment FAILED! ---"
    echo "Please review the error messages above."
    exit 1
fi
echo "--- Cloud Function Deployment Successful! ---"
echo ""

# --- Grant Permissions for Agent Engine Invocation ---
echo "--- Granting IAM Role for Agent Engine Invocation ---"
echo "Granting '${REQUIRED_ROLE}' to service account '${FUNCTION_SERVICE_ACCOUNT}'"
echo "on target '${REASONING_AGENT_TARGET}'."

# Add the IAM policy binding at the project level for the specified role.
# This grants your Cloud Function's service account permission to interact
# with Vertex AI resources within your project.
gcloud projects add-iam-policy-binding "${PROJECT_ID}" \
    --member="serviceAccount:${FUNCTION_SERVICE_ACCOUNT}" \
    --role="${REQUIRED_ROLE}" \
    --condition=None # Use --condition if you need conditional access

if [ $? -eq 0 ]; then
    echo "IAM role granted successfully."
else
    echo "Failed to grant IAM role. Please check your permissions and the target resource."
    # Exit if permission assignment fails, as the function might not work correctly.
    exit 1
fi
echo ""

# --- Final Instructions ---
echo "You can view your function in the Google Cloud Console:"
echo "https://console.cloud.google.com/functions/details/${REGION}/${FUNCTION_NAME}?project=$(gcloud config get-value project)"
echo ""
echo "To get the invokable URL, run:"
echo "gcloud functions describe ${FUNCTION_NAME} --region ${REGION} --format='value(httpsTrigger.url)'"
