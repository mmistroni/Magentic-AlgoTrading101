#!/bin/bash

# --- Start of Script ---

# 1. Check for Active Google Cloud Authentication
echo "--- Checking Google Cloud Authentication Status ---"

# The 'gcloud auth print-access-token' command will fail if not logged in.
# We redirect output to /dev/null to keep the console clean.
gcloud auth print-access-token --quiet > /dev/null 2>&1

# Check the exit code of the last command ($?)
if [ $? -ne 0 ]; then
    echo "❌ ERROR: You are not authenticated with gcloud."
    echo "🚨 Please run the following command to log in, then re-run this script:"
    echo "   gcloud auth login"
    exit 1 # Exit the script with an error code
fi

echo "✅ Authentication successful. Proceeding with deployment..."

# ---

# 2. Define Variables
# NOTE: The values for these variables will be read from your shell environment.
# If they are NOT set, the script will use the default values provided below.

# GCLOUD Project and Location (Mandatory for the deploy command)
GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-datascience-projects}"
GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

# Service Name (Used in the deploy command)
SERVICE_NAME="congress-trades-agent"

# Agent-Specific Environment Variables (Necessary for your service to run)
# Update 'your-vertex-setting' with 'true' or 'false'
GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-true}"

# 3. Check and Print Variables for Confirmation
echo ""
echo "--- Deployment Configuration ---"
echo "Project:  $GOOGLE_CLOUD_PROJECT"
echo "Region:   $GOOGLE_CLOUD_LOCATION"
echo "Service:  $SERVICE_NAME"
echo "--- Environment Variables to be set on Cloud Run service ---"
echo "  GOOGLE_CLOUD_PROJECT:       $GOOGLE_CLOUD_PROJECT"
echo "  GOOGLE_CLOUD_LOCATION:      $GOOGLE_CLOUD_LOCATION"
echo "  GOOGLE_GENAI_USE_VERTEXAI:  $GOOGLE_GENAI_USE_VERTEXAI"
echo "--------------------------------"


# 4. Construct the Environment Variables String for the gcloud command
ENV_VARS_STRING="GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI"


# 5. Execute the gcloud run deploy command
echo "Executing gcloud run deploy..."
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS_STRING" \
  --platform managed

# 6. Provide a Completion Message
if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Deployment of $SERVICE_NAME to Google Cloud Run **successful**!"
else
  echo ""
  echo "❌ Deployment failed. Please check the error messages above."
fi

# --- End of Script ---