#!/bin/bash

# --- CONFIGURATION ---
REGION="us-central1"
IMAGE_NAME="gcr.io/datascience-projects/congress-bot:latest"
JOB_NAME="contract-backfill"
PROJECT_ID="datascience-projects"

echo "--- 1. Building Image ---"
# This ensures the new 'scripts/backfill_contracts.py' is actually inside the container
gcloud builds submit --tag $IMAGE_NAME . --project $PROJECT_ID

echo "--- 2. Creating/Updating Job ---"
if gcloud run jobs describe $JOB_NAME --region $REGION > /dev/null 2>&1; then
    COMMAND="update"
else
    COMMAND="create"
fi

# The --args flag points to the file location INSIDE the container (/app/scripts/...)
gcloud run jobs $COMMAND $JOB_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --command python \
  --args scripts/backfill_contracts.py \
  --set-env-vars PROJECT_ID=$PROJECT_ID \
  --max-retries 0 \
  --task-timeout=24h \
  --memory=2Gi

echo "--- 3. Executing Job ---"
#gcloud run jobs execute $JOB_NAME --region $REGION