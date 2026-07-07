#!/bin/bash
set -e

# --- CONFIGURATION ---
PROJECT_ID="datascience-projects"
REGION="us-central1"
JOB_NAME="lobbying-daily-job"
IMAGE_NAME="lobbying-daily-downloader"

# Target URL for the built image
IMAGE_URL="gcr.io/${PROJECT_ID}/${IMAGE_NAME}:latest"

echo "⏳ Backing up existing main Dockerfile if it exists..."
if [ -f Dockerfile ]; then
    mv Dockerfile Dockerfile.bak
    HAD_BAK=true
else
    HAD_BAK=false
fi

# Set up clean exit handling to restore files if the build crashes midway
cleanup() {
    echo "🧹 Cleaning up temporary build states..."
    rm -f Dockerfile
    if [ "$HAD_BAK" = true ]; then
        mv Dockerfile.bak Dockerfile
        echo "🔄 Restored your original main Dockerfile."
    fi
}
trap cleanup EXIT

echo "📝 Preparing custom lobbying context..."
cp Dockerfile.lobbying Dockerfile

echo "📦 1. Building container remotely with Cloud Build..."
# ADDED THE --project FLAG HERE
gcloud builds submit --project $PROJECT_ID --tag $IMAGE_URL .

echo "☁️ 2. Deploying Cloud Run Job from the built image..."
gcloud run jobs deploy $JOB_NAME \
    --image $IMAGE_URL \
    --region $REGION \
    --project $PROJECT_ID \
    --set-env-vars PROJECT_ID=$PROJECT_ID \
    --max-retries 2 \
    --task-timeout 10m

echo "✅ Cloud Run Job '$JOB_NAME' successfully deployed!"
echo "💡 To trigger it manually right now, run:"
echo "   gcloud run jobs execute $JOB_NAME --region $REGION"