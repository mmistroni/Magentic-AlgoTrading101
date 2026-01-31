#!/bin/bash

# --- 1. Authentication Check ---
echo "--- Checking Google Cloud Authentication ---"
gcloud auth print-access-token --quiet > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Not authenticated. Run 'gcloud auth login' first."
    exit 1
fi
echo "✅ Authenticated."

# --- 2. Variable Mapping ---
GCP_PROJECT="$PROJECT_ID"
SERVICE_NAME="crawler-agent-service"
GCP_LOCATION="us-central1"
API_KEY="$SENDGRID_KEY"

# --- 3. Validation ---
if [ -z "$GCP_PROJECT" ]; then
    echo "❌ ERROR: PROJECT_ID environment variable is not set."
    exit 1
fi

if [ -z "$API_KEY" ]; then
    echo "⚠️  WARNING: SENDGRID_KEY (for SendGrid) is not set."
fi

# --- 4. Deployment Configuration ---
# We add GOOGLE_GENAI_USE_VERTEXAI=True so the ADK uses the Service Account
ENV_VARS="GOOGLE_CLOUD_PROJECT=$GCP_PROJECT"
ENV_VARS="$ENV_VARS,GOOGLE_CLOUD_LOCATION=$GCP_LOCATION"
ENV_VARS="$ENV_VARS,GOOGLE_GENAI_USE_VERTEXAI=True"
ENV_VARS="$ENV_VARS,EMAIL_API_KEY=$API_KEY"
ENV_VARS="$ENV_VARS,SENDER_EMAIL=$SENDER_EMAIL"
ENV_VARS="$ENV_VARS,RECIPIENT_EMAIL=$RECIPIENT_EMAIL"
ENV_VARS="$ENV_VARS,PLAYWRIGHT_BROWSERS_PATH=/ms-playwright"

echo ""
echo "---------------------------------------------------"
echo "🚀 Deploying to Cloud Run (Vertex AI Mode)"
echo "🆔 Project: $GCP_PROJECT"
echo "🧠 Memory:  1Gi"
echo "---------------------------------------------------"
echo ""

# --- 5. The Deploy Command ---
gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$GCP_LOCATION" \
  --project "$GCP_PROJECT" \
  --memory 1Gi \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS" \
  --platform managed

# --- 6. Results ---
if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Deployment Successful!"
  URL=$(gcloud run services describe "$SERVICE_NAME" --region "$GCP_LOCATION" --project "$GCP_PROJECT" --format='value(status.url)')
  echo "🌍 Service URL: $URL"
else
  echo ""
  echo "❌ Deployment failed."
fi