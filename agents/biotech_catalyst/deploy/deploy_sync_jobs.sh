#!/bin/bash
set -e

PROJECT_ID="datascience-projects"
REGION="us-central1"
IMAGE_TAG="gcr.io/${PROJECT_ID}/short-selling-jobs:latest"

echo "🎯 Targeted Project Space: ${PROJECT_ID} in ${REGION}"

# 1. Temporarily copy Dockerfile.jobs to standard Dockerfile for Cloud Build compatibility
echo "📋 Setting up Dockerfile context..."
cp Dockerfile.jobs Dockerfile

# 2. Submit the build cleanly (it picks up 'Dockerfile' by default)
echo "📦 Compiling and pushing multi-purpose job container..."
gcloud builds submit . --tag "${IMAGE_TAG}" --project="${PROJECT_ID}"

# Clean up the temporary file locally
rm Dockerfile

# 3. Deploy Cloud Run Job A: SEC Ticker Master Sync
echo "🚀 Provisioning Cloud Run Job: sec-sync..."
gcloud run jobs deploy sec-sync \
  --image="${IMAGE_TAG}" \
  --command="python" \
  --args="sec_sync.py" \
  --region="${REGION}" \
  --project="${PROJECT_ID}"

# 4. Deploy Cloud Run Job B: Biotech Catalyst Sync
echo "🚀 Provisioning Cloud Run Job: sync-catalyst-job..."
gcloud run jobs deploy sync-catalyst-job \
  --image="${IMAGE_TAG}" \
  --command="python" \
  --args="sync_catalyst_job.py,--days,2" \
  --region="${REGION}" \
  --project="${PROJECT_ID}"

echo "✨ Configuration verified. Both jobs are deployed via your user credentials!"