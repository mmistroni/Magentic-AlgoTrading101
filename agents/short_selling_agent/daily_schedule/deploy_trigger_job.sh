#!/bin/bash

# Exit immediately if a command exits with a non-zero status
set -e

# --- Configuration ---
JOB_NAME="daily-short-selling-scan"
REGION="us-central1"
AGENT_SERVICE_URL="https://short-selling-agent-service-682143946483.us-central1.run.app"

# Get current directory name
CURRENT_DIR=$(basename "$PWD")

# 1. Verification Check: Ensure the user is executing this inside the daily_schedule directory
if [ "$CURRENT_DIR" != "daily_schedule" ]; then
    echo "❌ ERROR: Please run this script from inside the 'daily_schedule' directory."
    echo "👉 Run: cd agents/short_selling_agent/daily_schedule && ./deploy.sh"
    exit 1
fi

echo "🚀 Starting automated source deployment for Cloud Run Job: ${JOB_NAME}..."

# 2. Extract active GCP Project ID from the local gcloud CLI config
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

# 3. Execute the single deploy command
gcloud run jobs deploy "${JOB_NAME}" \
    --source . \
    --region="${REGION}" \
    --set-env-vars="AGENT_SERVICE_URL=${AGENT_SERVICE_URL},SENDGRID_API_KEY=${SENDGRID_KEY},EMAIL_PASSWORD=${EMAIL_PASSWORD}" \
    --max-retries=3 \
    --task-timeout=300s

echo "====================================================================="
echo "🎉 SUCCESS: Job '${JOB_NAME}' has been compiled, built, and deployed!"
echo "👉 You can run a manual test in the cloud using:"
echo "   gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo "====================================================================="