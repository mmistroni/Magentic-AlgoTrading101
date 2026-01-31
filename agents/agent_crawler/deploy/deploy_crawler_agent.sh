#!/bin/bash

# --- 1. Authentication Check ---
gcloud auth print-access-token --quiet > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Run 'gcloud auth login' first."
    exit 1
fi

# --- 2. Variable Mapping ---
GCP_PROJECT="$PROJECT_ID"
SERVICE_NAME="crawler-agent-service"
GCP_LOCATION="us-central1"
API_KEY="$SENDGRID_KEY"

# --- 3. Construct Environment Variables ---
# We force 2GiB to stop the Ray-Ban memory crashes.
# We set VertexAI to True for the Service Account to work.
ENV_VARS="GOOGLE_CLOUD_PROJECT=$GCP_PROJECT"
ENV_VARS="$ENV_VARS,GOOGLE_CLOUD_LOCATION=$GCP_LOCATION"
ENV_VARS="$ENV_VARS,GOOGLE_GENAI_USE_VERTEXAI=True"
ENV_VARS="$ENV_VARS,EMAIL_API_KEY=$API_KEY"
ENV_VARS="$ENV_VARS,SENDER_EMAIL=$SENDER_EMAIL"
ENV_VARS="$ENV_VARS,RECIPIENT_EMAIL=$RECIPIENT_EMAIL"
ENV_VARS="$ENV_VARS,PLAYWRIGHT_BROWSERS_PATH=/ms-playwright"

echo "🚀 Deploying $SERVICE_NAME with 2GiB RAM..."

gcloud run deploy "$SERVICE_NAME" \
  --source . \
  --region "$GCP_LOCATION" \
  --project "$GCP_PROJECT" \
  --memory 2Gi \
  --allow-unauthenticated \
  --set-env-vars="$ENV_VARS" \
  --platform managed