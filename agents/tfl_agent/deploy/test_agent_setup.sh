#!/bin/bash

export APP_URL="https://tfl-agent-service-682143946483.us-central1.run.app"
export TOKEN=$(gcloud auth print-identity-token)

echo "🚀 Triggering TfL Route Check Agent..."

# We call the specific route defined in your main.py: @app.post("/trigger-route-check")
curl -i -X POST "$APP_URL/trigger-route-check" \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{
        "query": "Find the best 3 routes from Fairlop to Bromley South for tomorrow departing at 05:45. Apply the delay penalty logic and format the result for a WhatsApp notification.",
        "subject_line": "TfL Journey: Fairlop to Bromley",
        "recipient": "mmistroni@gmail.com"
    }'

echo -e "\n\n✅ Request sent. Check your Cloud Run logs or email for the agent output."