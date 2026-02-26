##  Agent on Cloud Run - 
TFL Agent

sample prompt

system_prompt=(
        "Use the 'get_tfl_journeys' tool to find routes from Fairlop to Bromley South. "
        "Analyze the results, sort the top 3 by price and delays, and "
        "format a WhatsApp message for the user."
    )

-- standard prompot
Find the best 3 routes from Fairlop to Bromley South for tomorrow departing at 05:45. Apply the delay penalty logic and format the result for a WhatsApp notification.


# printf '%s' "$GCP_SA_KEY" > /workspaces/Magentic-AlgoTrading101/gcp_key.json

# 1. The most critical one: Points the code to your JSON file
export GOOGLE_APPLICATION_CREDENTIALS="/workspaces/Magentic-AlgoTrading101/gcp_key.json"

# 2. Sets the default project so you don't have to hardcode it in Python
export GOOGLE_CLOUD_PROJECT="datascience-projects"

# 3. Tells gcloud (and some libraries) which project to bill for API usage
export GOOGLE_CLOUD_QUOTA_PROJECT="datascience-projects"