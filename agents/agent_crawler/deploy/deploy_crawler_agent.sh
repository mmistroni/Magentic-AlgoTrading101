#!/bin/bash

# --- 1. Authentication Check ---
echo "--- Checking Google Cloud Authentication ---"
gcloud auth print-access-token --quiet > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Not authenticated. Run 'gcloud auth login'."
    exit 1
fi
echo "✅ Authenticated."

# --- 2. Configuration Variables ---
# Replace 'your-project-id' with your actual Google Cloud Project ID
GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-your-project-id}"
GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"
SERVICE_NAME="crawler-agent-service"

# Agent & Feature Settings
GOOGLE_GENAI_USE_VERTEXAI="${GOOGLE_GENAI_USE_VERTEXAI:-false}"

# --- 3. Secret & Environment Variable Prep ---
# Note: It's best practice to set these in your terminal session before running:
# export EMAIL_API_KEY="SG.xxx"
# export SENDER_EMAIL="me@domain.com"
# export RECIPIENT_EMAIL="target@domain.com"

if [[ -z "$EMAIL_API_KEY" || -z "$SENDER_EMAIL" ]]; then
    echo "⚠️  WARNING: EMAIL_API_KEY or SENDER_EMAIL is not set in your shell."
    echo "The agent may fail to send reports."
fi

# Build the environment string
ENV_VARS_STRING="GOOGLE_CLOUD_PROJECT=$GOOGLE_CLOUD_PROJECT"
ENV_VARS_STRING+=",GOOGLE_CLOUD_LOCATION=$GOOGLE_CLOUD_LOCATION"
ENV_VARS_STRING+=",GOOGLE_GENAI_USE_VERTEXAI=$GOOGLE_GENAI_USE_VERTEXAI"
ENV_VARS_STRING+=",EMAIL_API_KEY=$EMAIL_API_KEY"
ENV_VARS_STRING+=",SENDER_EMAIL=$SENDER_EMAIL"
ENV_VARS_STRING+=",RECIPIENT_EMAIL=$RECIPIENT_EMAIL"
# This ensures Playwright knows where we baked the browsers in the Dockerfile
ENV_VARS_STRING+=",PLAYWRIGHT_BROWSERS_PATH=/ms-playwright"

# --- 4. Summary ---
echo ""
echo "---------------------------------------------------"
echo "🚀 Deploying: $SERVICE_NAME"
echo "📍 Region:   $GOOGLE_CLOUD_LOCATION"
echo "🧠 Memory:   1Gi (Playwright Optimized)"
echo "🛠️  Project:  $GOOGLE_CLOUD_PROJECT"
echo "---------------------------------------------------"
echo ""

# --- 5. Deployment Command ---
# --memory 1Gi fixes your "Memory Limit Exceeded" error.
# --source . triggers the build using your updated Dockerfile.
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --memory 1Gi \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS_STRING" \
  --platform managed

# --- 6. Final Status ---
if [ $? -eq 0 ]; then
  echo ""
  echo "✅ SUCCESS: $SERVICE_NAME is live!"
  gcloud run services describe "$SERVICE_NAME" --platform managed --region "$GOOGLE_CLOUD_LOCATION" --format='value(status.url)'
else
  echo ""
  echo "❌ DEPLOYMENT FAILED. Check the logs above for Docker build errors."
fi