---  1 deleting api gtw

gcloud api-gateway gateways delete agent-gateway \
    --location=us-central1 \
    --project=datascience-projects \
    --quiet
    
-- List api configs
gcloud api-gateway api-configs list \
    --api=agent-api \
    --project=datascience-projects \
    --format="value(id)"


--- Delete each API Config you found:
gcloud api-gateway api-configs delete YOUR_API_CONFIG_ID \
    --api=agent-api \
    --project=datascience-projects \
    --quiet

--- delete api def

gcloud api-gateway apis delete agent-api \
    --project=datascience-projects \
    --quiet