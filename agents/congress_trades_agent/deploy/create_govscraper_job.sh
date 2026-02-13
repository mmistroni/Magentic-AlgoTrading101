#!/bin/bash

# --- CONFIGURATION ---
REGION="us-central1"
IMAGE_NAME="gcr.io/datascience-projects/congress-bot:latest"
JOB_NAME="contract-scraper"
PROJECT_ID="datascience-projects"

echo "--- 1. Checking Authentication ---"
gcloud auth print-access-token --quiet > /dev/null 2>&1
if [ $? -ne 0 ]; then
    echo "❌ ERROR: Not authenticated. Run 'gcloud auth login'."
    exit 1
fi

echo "--- 2. Building & Pushing Image via Cloud Build ---"
# This replaces 'docker build' and 'docker push'
gcloud builds submit --tag $IMAGE_NAME . --project $PROJECT_ID
if [ $? -ne 0 ]; then echo "❌ Cloud Build failed"; exit 1; fi

echo "--- 3. Updating Cloud Run Job ---"
if gcloud run jobs describe $JOB_NAME --region $REGION > /dev/null 2>&1; then
    COMMAND="update"
else
    COMMAND="create"
fi

gcloud run jobs $COMMAND $JOB_NAME \
  --image $IMAGE_NAME \
  --region $REGION \
  --command python \
  --args scripts/scraper_contracts.py \
  --set-env-vars PROJECT_ID=$PROJECT_ID \
  --max-retries 0 \
  --task-timeout=600s

echo "--- 4. Executing Job ---"
gcloud run jobs execute $JOB_NAME --region $REGION