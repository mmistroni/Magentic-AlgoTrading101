#!/bin/bash

# --- CONFIGURATION ---
REGION="us-central1"
# We use the same image name so we don't have to rebuild from scratch if cached
IMAGE_NAME="gcr.io/datascience-projects/congress-bot:latest"
# New Job Name specific for backfilling
JOB_NAME="contract-backfill"
PROJECT_ID="datascience-projects"

echo "--- 1. Checking Authentication ---"
gcloud auth print-access-token --quiet > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Not authenticated. Run 'gcloud auth login'."
    exit 1
fi

echo "--- 2. Building & Pushing Image via Cloud Build ---"
# Submit build to ensure the new backfill script is inside the container
gcloud builds submit --tag $IMAGE_NAME . --project $PROJECT_ID
if [ $? -ne 0 ]; then echo "❌ Cloud Build failed"; exit 1; fi

echo "--- 3. Creating/Updating Backfill Job ---"
# Check if job exists to determine update vs create
if gcloud run jobs describe $JOB_NAME --region $REGION > /dev/null 2>&1; then
    COMMAND="update"
else
    COMMAND="create"
fi

gcloud run jobs $COMMAND $JOB_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --command python \
  --args scripts/backfill_contracts.py \
  --set-env-vars PROJECT_ID=$PROJECT_ID \
  --max-retries 0 \
  --task-timeout=3600s \
  --memory=2Gi

# Note: Increased timeout to 3600s (1 hour) and Memory to 2GB for safety

echo "--- 4. Executing Backfill Job ---"
echo "This may take 20-30 minutes. You can close this terminal."
echo "View logs here: https://console.cloud.google.com/run/jobs/details/$REGION/$JOB_NAME/logs"

gcloud run jobs execute $JOB_NAME --region $REGION