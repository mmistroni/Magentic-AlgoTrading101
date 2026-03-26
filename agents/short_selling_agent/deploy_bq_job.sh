#!/bin/bash

# --- Start of Script ---

# 1. Check for Active Google Cloud Authentication
echo "--- Checking Google Cloud Authentication Status ---"
gcloud auth print-access-token --quiet > /dev/null 2>&1

if [ $? -ne 0 ]; then
    echo "❌ ERROR: You are not authenticated with gcloud."
    echo "🚨 Please run the following command to log in, then re-run this script:"
    echo "   gcloud auth login"
    exit 1
fi

echo "✅ Authentication successful. Proceeding with Job deployment..."

# ---

# 2. Define Variables
GOOGLE_CLOUD_PROJECT="${GOOGLE_CLOUD_PROJECT:-your-default-gcp-project-id}"
GOOGLE_CLOUD_LOCATION="${GOOGLE_CLOUD_LOCATION:-us-central1}"

# Job Name (Instead of Service Name)
JOB_NAME="short-selling-ingestion-job"

# API Keys (CRITICAL: You must set this in your terminal before running, or hardcode it here for testing)
FMP_API_KEY="${FMP_API_KEY:-your_fmp_api_key_here}"

# 3. Check and Print Variables for Confirmation
echo ""
echo "--- Job Deployment Configuration ---"
echo "Project:  $GOOGLE_CLOUD_PROJECT"
echo "Region:   $GOOGLE_CLOUD_LOCATION"
echo "Job Name: $JOB_NAME"
echo "--- Environment Variables to be set on Cloud Run Job ---"
echo "  GCP_PROJECT_ID: $GOOGLE_CLOUD_PROJECT"
echo "  FMP_API_KEY:    [HIDDEN FOR SECURITY]"
echo "--------------------------------"

# 4. Construct the Environment Variables String
# Fixed typo here: changed $FMP_KEY to $FMP_API_KEY
ENV_VARS_STRING="GCP_PROJECT_ID=$GOOGLE_CLOUD_PROJECT,FMP_API_KEY=$FMP_KEY"

# 5. Execute the gcloud run jobs deploy command
echo "Executing gcloud run jobs deploy..."
gcloud run jobs deploy "$JOB_NAME" \
  --source . \
  --region "$GOOGLE_CLOUD_LOCATION" \
  --project "$GOOGLE_CLOUD_PROJECT" \
  --set-env-vars="$ENV_VARS_STRING" \
  --command="python" \
  --args="-m,short_selling_agent.bq_ingestion"

# 6. Provide a Completion Message and Kick Off the Job
if [ $? -eq 0 ]; then
  echo ""
  echo "✅ Deployment of JOB $JOB_NAME to Google Cloud Run **successful**!"
  echo "🚀 Kicking off the job execution now..."
  
  # This command executes the job immediately
  gcloud run jobs execute "$JOB_NAME" \
    --region "$GOOGLE_CLOUD_LOCATION" \
    --project "$GOOGLE_CLOUD_PROJECT"

  echo ""
  echo "✅ Job execution triggered!"
  echo "📊 You can monitor the logs live by running:"
  echo "   gcloud run jobs logs tail $JOB_NAME --region $GOOGLE_CLOUD_LOCATION"
else
  echo ""
  echo "❌ Deployment failed. Please check the error messages above."
fi

# --- End of Script ---