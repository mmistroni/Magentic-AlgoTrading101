#!/bin/bash

# --- Start of Script ---

# 1. Check for Active Google Cloud Authentication
echo "--- Checking Google Cloud Authentication Status ---"

# The 'gcloud auth print-access-token' command will fail if not logged in.
# We redirect output to /dev/null to keep the console clean.
gcloud auth print-access-token --quiet > /dev/null 2>&1

# Check the exit code of the last command ($?)
if [ $? -ne 0 ]; then
    echo "❌ ERROR: You are not authenticated with gcloud."
    echo "🚨 Please run the following command to log in, then re-run this script:"
    echo "   gcloud auth login"
    exit 1 # Exit the script with an error code
fi

echo "✅ Authentication successful. Proceeding with deployment..."
gcloud run jobs execute contract-scraper
# ---

# Check if the job already exists
if gcloud run jobs describe contract-scraper --region us-central1 > /dev/null 2>&1; then
    echo "🔄 Job exists. Updating..."
    COMMAND="update"
else
    echo "🆕 Job not found. Creating..."
    COMMAND="create"
fi

gcloud run jobs $COMMAND contract-scraper \
  --image gcr.io/datascience-projects/congress-bot:latest \
  --region us-central1 \
  --command python \
  --args scripts/scraper_contracts.py \
  --set-env-vars PROJECT_ID=datascience-projects \
  --max-retries 0