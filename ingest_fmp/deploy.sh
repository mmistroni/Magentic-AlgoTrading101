#!/bin/bash
set -e

# Configuration variables
PROJECT_ID="datascience-projects"
REGION="europe-west1"
IMAGE_NAME="gcr.io/${PROJECT_ID}/ingest-fmp:latest"

# Target BigQuery temporary table ID
BIGQUERY_TABLE_ID="${PROJECT_ID}.gcp_shareloader.tmp_finviz_selection"

# Verify that FMP_API_KEY is present in your shell session before proceeding
if [ -z "${FMP_API_KEY}" ]; then
    echo "❌ Error: FMP_API_KEY environment variable is not set."
    echo "Please export it first: export FMP_API_KEY='your_actual_key_here'"
    exit 1
fi

echo "🔨 Building container image via Cloud Build..."
gcloud builds submit --tag ${IMAGE_NAME} .

# Define the 6 pipelines (Job Name -> PIPELINE_NAME env var)
declare -A PIPELINES=(
    ["fmp-eod-job"]="eod"
    ["fmp-extra-job"]="extra"
    ["fmp-market-down-job"]="market_down"
    ["fmp-high-growth-float-job"]="high_growth_float"
    ["fmp-swing-trading-job"]="swing_trading"
    ["fmp-new-highs-job"]="new_highs"
)

echo "🚀 Deploying/Updating Cloud Run Jobs with BigQuery and FMP integration..."

for JOB_NAME in "${!PIPELINES[@]}"; do
    PIPELINE_VAL="${PIPELINES[$JOB_NAME]}"
    echo "----------------------------------------"
    echo "Deploying Job: $JOB_NAME (Pipeline: $PIPELINE_VAL)"
    
    # Bundle environment variables for the job task (Fixed FMP_API_KEY reference)
    ENV_VARS="PIPELINE_NAME=$PIPELINE_VAL,BIGQUERY_TABLE_ID=$BIGQUERY_TABLE_ID,FMP_API_KEY=$FMP_API_KEY"

    if gcloud run jobs describe "$JOB_NAME" --region="$REGION" &>/dev/null; then
        echo "Updating existing job $JOB_NAME..."
        gcloud run jobs update "$JOB_NAME" \
            --image="$IMAGE_NAME" \
            --set-env-vars="$ENV_VARS" \
            --region="$REGION" \
            --max-retries=0 \
            --task-timeout=7200s
    else
        echo "Creating new job $JOB_NAME..."
        gcloud run jobs create "$JOB_NAME" \
            --image="$IMAGE_NAME" \
            --set-env-vars="$ENV_VARS" \
            --region="$REGION" \
            --max-retries=0 \
            --task-timeout=7200s
    fi
done

echo "✨ All 6 Cloud Run Jobs deployed successfully with a 2-hour timeout!"