#!/bin/bash

# This script deploys a Google Cloud Function to the specified region.
# It assumes you have the Google Cloud SDK installed and authenticated.

# --- Configuration Variables ---
# You can modify these variables to match your function's details.

# The name of your Cloud Function (must be unique within your project and region).
FUNCTION_NAME="my_agent_function"

# The entry point for your function (the Python function name to execute).
# Based on our discussion, this could be 'pinco' or 'hello_world'.
ENTRY_POINT="execute_call"

# The runtime for your function (e.g., python39, python311).
RUNTIME="python311"

# The Google Cloud region where you want to deploy your function.
# Choose a region close to your users or services.
# Examples: europe-west2 (London), us-central1, asia-east1.
REGION="us-central1"

# The source directory containing your function's main.py and requirements.txt.
# '.' means the current directory where you run this script.
# If your function files are in a subfolder (e.g., 'my_function_code'), set it like:
# SOURCE_DIR="./my_function_code"
SOURCE_DIR="."

# --- Deployment Command ---
echo "--- Starting Google Cloud Function Deployment ---"
echo "Function Name: ${FUNCTION_NAME}"
echo "Entry Point: ${ENTRY_POINT}"
echo "Runtime: ${RUNTIME}"
echo "Region: ${REGION}"
echo "Source Directory: ${SOURCE_DIR}"
echo ""

# Execute the gcloud functions deploy command
# --trigger-http makes it a callable HTTP function.
# --allow-unauthenticated allows public access to the function.
#   If you want to restrict access, remove this flag and configure IAM permissions.
gcloud functions deploy "${FUNCTION_NAME}" \
    --runtime "${RUNTIME}" \
    --trigger-http \
    --entry-point "${ENTRY_POINT}" \
    --region "${REGION}" \
    --source="${SOURCE_DIR}" \
    --allow-unauthenticated # Consider removing for production if authentication is required

# --- Check Deployment Status ---
if [ $? -eq 0 ]; then
    echo ""
    echo "--- Cloud Function Deployment Successful! ---"
    echo "You can view your function in the Google Cloud Console:"
    echo "https://console.cloud.google.com/functions/details/${REGION}/${FUNCTION_NAME}?project=$(gcloud config get-value project)"
    echo ""
    echo "To get the invokable URL, run:"
    echo "gcloud functions describe ${FUNCTION_NAME} --region ${REGION} --format='value(httpsTrigger.url)'"
else
    echo ""
    echo "--- Cloud Function Deployment FAILED! ---"
    echo "Please review the error messages above."
    exit 1
fi
