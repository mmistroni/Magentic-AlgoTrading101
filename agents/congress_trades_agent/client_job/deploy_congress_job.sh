#!/usr/bin/env bash
set -euo pipefail

# --- Configuration ---
JOB_NAME="congress-trades-daily-job"
REGION="us-central1"
AGENT_SERVICE_URL="${AGENT_SERVICE_URL:-https://congress-trades-agent-682143946483.us-central1.run.app}"
EMAIL_SUBJECT_PREFIX="${EMAIL_SUBJECT_PREFIX:-[CONGRESS_TRADES_AGENT]}"
REPORT_EMAIL="${REPORT_EMAIL:-mmistroni@gmail.com}"

# 1. Pre-flight Check: Ensure EMAIL_PASSWORD is set locally
if [ -z "${EMAIL_PASSWORD:-}" ]; then
    echo "🚨 ERROR: EMAIL_PASSWORD environment variable is not set in your local shell!"
    echo "👉 Run: export EMAIL_PASSWORD='your_app_password' before executing this script."
    exit 1
fi

echo "🚀 Starting automated source deployment for Cloud Run Job: ${JOB_NAME}..."

# 2. Extract active GCP Project ID from local gcloud CLI config
GCP_PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)

if [ -z "$GCP_PROJECT_ID" ]; then
    echo "❌ ERROR: No active Google Cloud Project detected in gcloud CLI."
    echo "👉 Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "📡 Target Project ID: ${GCP_PROJECT_ID}"
echo "📡 Target Region:     ${REGION}"
echo "📡 Agent Target URL:  ${AGENT_SERVICE_URL}"
echo "🔨 Submitting source to Google Cloud Build and deploying job..."

# 3. Execute single source-deploy command
gcloud run jobs deploy "${JOB_NAME}" \
    --source . \
    --region="${REGION}" \
    --project="${GCP_PROJECT_ID}" \
    --set-env-vars="AGENT_SERVICE_URL=${AGENT_SERVICE_URL},GCP_PROJECT=${GCP_PROJECT_ID},EMAIL_PASSWORD=${EMAIL_PASSWORD},EMAIL_SUBJECT_PREFIX=${EMAIL_SUBJECT_PREFIX},REPORT_EMAIL=${REPORT_EMAIL}" \
    --max-retries=1 \
    --task-timeout=600s

echo "====================================================================="
echo "🎉 SUCCESS: Job '${JOB_NAME}' has been compiled, built, and deployed!"
echo "👉 You can run a manual test in the cloud using:"
echo "   gcloud run jobs execute ${JOB_NAME} --region=${REGION}"
echo "👉 Or pass a specific analysis_date override:"
echo "   gcloud run jobs execute ${JOB_NAME} --region=${REGION} --args=2026-05-11"
echo "====================================================================="