

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


gcloud api-gateway apis list --project=datascience-projects


gcloud api-gateway gateways list --project=datascience-projects --location=YOUR_REGION


For this example, we've enabled API Key authentication. Any calls to your gateway
will require the 'X-Api-Key: YOUR_API_KEY' header.
You can set up quota limits for this API Service in the GCP Console manually.

--- API Gateway Deployment Process Initiated (with API Key security via headers)! ---
It may take several minutes for the gateway to become fully operational.
Once the gateway status is 'ACTIVE', you can find its URL by running:
gcloud api-gateway gateways describe agent-gateway2 --location=us-central1 --project=datascience-projects --format='value(defaultHostname)'

Once the gateway is active, your function will be accessible at:
https://<GATEWAY_URL>/hello
Example Postman/cURL usage:
  GET: https://<GATEWAY_URL>/hello?name=APIUser
       Header: X-Api-Key: 
  POST: https://<GATEWAY_URL>/hello
        Header: X-Api-Key: 
        Body (raw, JSON): {'name': 'PostmanJSON'}

Keep your API Key secret! This key controls access to your API.
You can manage API keys in the Google Cloud Console: https://console.cloud.google.com/apis/credentials?project=datascience-projects
vscode@codespaces-5c1a68:/workspaces/Magentic-AlgoTrading101/agent_cloud_function$ 