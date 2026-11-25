#!/usr/bin/env bash
set -euo pipefail

# --- Configuration ---
JOB_NAME="congress-trades-daily-job"
SCHEDULER_JOB_NAME="congress-trades-daily-schedule"
REGION="us-central1"
SCHEDULER_REGION="${SCHEDULER_REGION:-europe-west2}"

# Early morning UK time (06:00 Europe/London) by default
SCHEDULE_CRON="${SCHEDULE_CRON:-0 6 * * *}"
SCHEDULE_TZ="${SCHEDULE_TZ:-Europe/London}"
SCHEDULER_SA="${SCHEDULER_SA:-}" # Optional: service account email with Cloud Run Invoker

AGENT_SERVICE_URL="${AGENT_SERVICE_URL:-https://congress-trades-agent-682143946483.us-central1.run.app}"
EMAIL_SUBJECT_PREFIX="${EMAIL_SUBJECT_PREFIX:-[CONGRESS_TRADES_AGENT]}"
REPORT_EMAIL="${REPORT_EMAIL:-mmistroni@gmail.com}"

# 1. Pre-flight Check: Ensure EMAIL_PASSWORD is set locally
if [ -z "${EMAIL_PASSWORD:-}" ]; then
    echo "🚨 ERROR: EMAIL_PASSWORD environment variable is not set in your local shell!"
    echo "👉 Run: export EMAIL_PASSWORD='your_app_password' before executing this script."
    exit 1
fi

# 2. Extract active GCP Project ID from local gcloud CLI config
GCP_PROJECT_ID=$(gcloud config get-value project 2>/dev/null || true)
if [ -z "$GCP_PROJECT_ID" ]; then
    echo "❌ ERROR: No active Google Cloud Project detected in gcloud CLI."
    echo "👉 Please run: gcloud config set project YOUR_PROJECT_ID"
    exit 1
fi

echo "🚀 Deploying Cloud Run Job: ${JOB_NAME} in ${REGION} (${GCP_PROJECT_ID})..."
gcloud run jobs deploy "${JOB_NAME}" \
    --source . \
    --region="${REGION}" \
    --project="${GCP_PROJECT_ID}" \
    --set-env-vars="AGENT_SERVICE_URL=${AGENT_SERVICE_URL},GCP_PROJECT=${GCP_PROJECT_ID},EMAIL_PASSWORD=${EMAIL_PASSWORD},EMAIL_SUBJECT_PREFIX=${EMAIL_SUBJECT_PREFIX},REPORT_EMAIL=${REPORT_EMAIL}" \
    --max-retries=1 \
    --task-timeout=600s

# 3. Configure Cloud Scheduler Trigger
JOB_RUN_URI="https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${GCP_PROJECT_ID}/jobs/${JOB_NAME}:run"

echo "⏰ Configuring Cloud Scheduler trigger '${SCHEDULER_JOB_NAME}' in ${SCHEDULER_REGION} (${SCHEDULE_CRON} ${SCHEDULE_TZ})..."

SCHEDULER_AUTH_FLAGS=()
if [ -n "$SCHEDULER_SA" ]; then
    gcloud run jobs add-iam-policy-binding "${JOB_NAME}" \
        --region="${REGION}" \
        --project="${GCP_PROJECT_ID}" \
        --member="serviceAccount:${SCHEDULER_SA}" \
        --role="roles/run.invoker" \
        --quiet

    SCHEDULER_AUTH_FLAGS+=(
        --oidc-service-account-email="${SCHEDULER_SA}"
        --oidc-token-audience="https://${REGION}-run.googleapis.com"
    )
fi

if gcloud scheduler jobs describe "${SCHEDULER_JOB_NAME}" \
    --location="${SCHEDULER_REGION}" \
    --project="${GCP_PROJECT_ID}" >/dev/null 2>&1; then
    gcloud scheduler jobs update http "${SCHEDULER_JOB_NAME}" \
        --location="${SCHEDULER_REGION}" \
        --project="${GCP_PROJECT_ID}" \
        --schedule="${SCHEDULE_CRON}" \
        --time-zone="${SCHEDULE_TZ}" \
        --uri="${JOB_RUN_URI}" \
        --http-method=POST \
        --attempt-deadline=600s \
        "${SCHEDULER_AUTH_FLAGS[@]}"
else
    gcloud scheduler jobs create http "${SCHEDULER_JOB_NAME}" \
        --location="${SCHEDULER_REGION}" \
        --project="${GCP_PROJECT_ID}" \
        --schedule="${SCHEDULE_CRON}" \
        --time-zone="${SCHEDULE_TZ}" \
        --uri="${JOB_RUN_URI}" \
        --http-method=POST \
        --attempt-deadline=600s \
        "${SCHEDULER_AUTH_FLAGS[@]}"
fi

echo "====================================================================="
echo "🎉 SUCCESS: Job '${JOB_NAME}' and schedule '${SCHEDULER_JOB_NAME}' are configured!"
echo "👉 Run schedule now:  gcloud scheduler jobs run ${SCHEDULER_JOB_NAME} --location=${SCHEDULER_REGION}"
echo "👉 Check job logs:    gcloud run jobs executions list --job=${JOB_NAME} --region=${REGION}"
echo "====================================================================="