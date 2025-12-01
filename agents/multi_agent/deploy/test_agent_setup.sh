export APP_URL="https://multi-agent-service-682143946483.us-central1.run.app"
# Example: export APP_URL="https://adk-default-service-name-abc123xyz.a.run.app"
export TOKEN=$(gcloud auth print-identity-token)

echo 'Listing Apps'

curl -X GET -H "Authorization: Bearer $TOKEN" $APP_URL/list-apps

echo 'Creating session......'
curl -X POST -H "Authorization: Bearer $TOKEN" \
    $APP_URL/apps/multi_agent/users/user_123/sessions/session_abc \
    -H "Content-Type: application/json" \
    -d '{"state": {"preferred_language": "English", "visit_count": 5}}'

echo 'Running Requests...'

curl -X POST -H "Authorization: Bearer $TOKEN" \
    $APP_URL/run_sse \
    -H "Content-Type: application/json" \
    -d '{
    "app_name": "multi_agent",
    "user_id": "user_123",
    "session_id": "session_abc",
    "new_message": {
        "role": "user",
        "parts": [{
        "text": "Please suggest me places to visit in paris in july for a honeymoon and book flight from london and a 5 night stay at a 4 star hotel"
        }]
    },
    "streaming": false
    }'