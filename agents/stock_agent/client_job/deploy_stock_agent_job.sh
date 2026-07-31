#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# --- Configuration ---
JOB_NAME="stock-agent-daily-job"
REGION="us-central1"
AGENT_SERVICE_URL="https://stock-agent-service-682143946483.us-central1.run.app"

# Get current directory name
CURRENT_DIR=$(basename "$PWD")

# 1. Verification Check: Ensure the user is executing this inside the client_job directory
if [ "$CURRENT_DIR" != "client_job" ]; then
    echo "❌ ERROR: Please run this script from inside the 'client_job' directory."
    echo "👉 Run: cd client_job && ./deploy.sh"
    exit 1
fi

# 2. Pre-flight Check: Ensure EMAIL_PASSWORD is set locally
if [ -z "${EMAIL_PASSWORD}" ]; then
  echo "🚨 ERROR: EMAIL_PASSWORD environment variable is not set in your local shell!"
  echo "👉 Run: export EMAIL_PASSWORD='your_app_password' before executing this script."
  exit 1
fi

echo "🚀 Starting automated source deployment for Cloud Run Job: ${JOB_NAME}..."

# 3. Extract active GCP Project ID from the local gcloud CLI config
GCP_PROJECT_ID=$(gcloud config get-value project 2>/dev/null)

if [ -z "$GCP_PROJECT_ID" ]; then
    echo "❌ ERROR: No active Google Cloud Project detected in gcloud CLI."
    echo "👉 Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📡 Target Project ID: ${GCP_PROJECT_ID}"
echo "📡 Target Region:     ${REGION}"
echo "📡 Agent Target URL:  ${AGENT_SERVICE_URL}"
echo "🔨 Submitting source to Google Cloud Build and deploying job..."

# 4. Execute single source-deploy command with cache-busting build arg
BUILD_TIMESTAMP=$(date +%s)

gcloud run jobs deploy "${JOB_NAME}" \
    --source . \
    --region="${REGION}" \
    --set-build-env-vars="BUILD_DATE=${BUILD_TIMESTAMP}" \
    --set-env-vars="AGENT_SERVICE_URL=${AGENT_SERVICE_URL},GCP_PROJECT=${GCP_PROJECT_ID},EMAIL_PASSWORD=${EMAIL_PASSWORD}" \
    --max-retries=1 \
    --task-timeout=600s


echo "====================================================================="
echo "🎉 SUCCESS: Job '${JOB_NAME}' has been compiled, built, and deployed!"
echo "👉 You can run a manual test in the cloud using:"
echo "   gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo "====================================================================="