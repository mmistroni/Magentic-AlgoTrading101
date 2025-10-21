export APP_URL="https://capital-agent-service-682143946483.us-central1.run.app"
# Example: export APP_URL="https://adk-default-service-name-abc123xyz.a.run.app"
export TOKEN=$(gcloud auth print-identity-token)
curl -X GET -H "Authorization: Bearer $TOKEN" $APP_URL/list-apps

curl -X POST -H "Authorization: Bearer $TOKEN" \
    $APP_URL/run_sse \
    -H "Content-Type: application/json" \
    -d '{
    "app_name": "capital_agent",
    "user_id": "user_123",
    "session_id": "session_abc",
    "new_message": {
        "role": "user",
        "parts": [{
        "text": "What is the capital of Canada?"
        }]
    },
    "streaming": false
    }'