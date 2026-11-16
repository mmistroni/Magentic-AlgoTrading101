#!/bin/bash

# --- Start of Script ---

# 1. Check for Active Google Cloud Authentication
echo "--- Checking Google Cloud Authentication Status ---"

gcloud auth print-access-token --quiet > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ ERROR: You are not authenticated with gcloud."
    echo "🚨 Please run the following command to log in, then re-run this script:"
    echo "   gcloud auth login"
    exit 1
fi

echo "✅ Authentication successful. Proceeding with deployment..."

# ---

# 2. Define and Verify Variables
GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-datascience-projects}"
GOOGLE_CLOUD_LOCATION="us-central1"
SERVICE_NAME="congress-trades-agent"
GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-true}"

# Ensure FMP_KEY is set in the environment
if [ -z "$FMP_KEY" ]; then
    echo "❌ ERROR: FMP_KEY environment variable is not set."
    echo "🚨 Please export your FMP key first: export FMP_KEY='your_key'"
    exit 1
fi

# 3. Print Configuration for Confirmation
echo ""
echo "--- Deployment Configuration ---"
echo "Project:  $GOOGLE_CLOUD_PROJECT"
echo "Region:   $GOOGLE_CLOUD_LOCATION"
echo "Service:  $SERVICE_NAME"
echo "--- Environment Variables to be set on Cloud Run service ---"
echo "  GOOGLE_CLOUD_PROJECT:       $GOOGLE_CLOUD_PROJECT"
echo "  GOOGLE_CLOUD_LOCATION:      $GOOGLE_CLOUD_LOCATION"
echo "  GOOGLE_GENAI_USE_VERTEXAI:  $GOOGLE_GENAI_USE_VERTEXAI"
echo "  FMP_API_KEY:                [PROVIDED VIA \$FMP_KEY]"
echo "--------------------------------"

# 4. Construct the Environment Variables String (mapping FMP_KEY to FMP_API_KEY)
ENV_VARS_STRING="GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT,GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION,GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI,FMP_API_KEY=$FMP_KEY"

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