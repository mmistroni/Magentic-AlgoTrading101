#!/usr/bin/env bash
set -e

# --- Configuration Variables ---
PROJECT_ID="datascience-projects"
REGION="us-central1"
REPOSITORY="cloud-run-source-deploy"
IMAGE_NAME="stock-agent-job"
JOB_NAME="stock-agent-daily-job"
SERVICE_ACCOUNT="stock-agent-job-sa@${PROJECT_ID}.iam.gserviceaccount.com" # Adjust if using default

FULL_IMAGE_URI="${REGION}-docker.pkg.dev/${PROJECT_ID}/${REPOSITORY}/${IMAGE_NAME}:latest"

echo "=========================================================="
echo "🚀 Building & Deploying Cloud Run Job: ${JOB_NAME}"
echo "=========================================================="

# 1. Ensure Artifact Registry repository exists
gcloud artifacts repositories describe ${REPOSITORY} \
    --location=${REGION} \
    --project=${PROJECT_ID} &>/dev/null || \
gcloud artifacts repositories create ${REPOSITORY} \
    --repository-format=docker \
    --location=${REGION} \
    --project=${PROJECT_ID} \
    --description="Docker repository for Cloud Run Jobs and Services"

# 2. Build and push container image using Cloud Build
echo "📦 Building container image via GCP Cloud Build..."
gcloud builds submit . \
    --tag="${FULL_IMAGE_URI}" \
    --project="${PROJECT_ID}"

# 3. Create or Update the Cloud Run Job
echo "⚡ Deploying Cloud Run Job..."
gcloud run jobs deploy ${JOB_NAME} \
    --image="${FULL_IMAGE_URI}" \
    --region="${REGION}" \
    --project="${PROJECT_ID}" \
    --set-env-vars="AGENT_SERVICE_URL=https://stock-agent-service-682143946483.us-central1.run.app,GCP_PROJECT=${PROJECT_ID}" \
    --max-retries=1 \
    --task-timeout=10m \
    --memory=512Mi \
    --cpu=1

echo "✅ Cloud Run Job '${JOB_NAME}' deployed successfully!"

# 4. Optional Execution Command
echo ""
echo "To execute the job manually, run:"
echo "  gcloud run jobs execute ${JOB_NAME} --region=${REGION} --project=${PROJECT_ID}"
echo ""
echo "To attach a daily Cloud Scheduler cron trigger (e.g., 08:30 AM UTC mon-fri):"
echo "  gcloud scheduler jobs create http ${JOB_NAME}-trigger \\"
echo "    --location=${REGION} \\"
echo "    --schedule='30 8 * * 1-5' \\"
echo "    --uri='https://${REGION}-run.googleapis.com/apis/run.googleapis.com/v1/namespaces/${PROJECT_ID}/jobs/${JOB_NAME}:run' \\"
echo "    --http-method=POST \\"
echo "    --oauth-service-account-email='YOUR_SERVICE_ACCOUNT_EMAIL'"