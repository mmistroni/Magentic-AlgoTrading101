import requests
import subprocess
import json
import argparse
import sys

def get_gcloud_identity_token():
    """
    Mimics $(gcloud auth print-identity-token)
    """
    try:
        token = subprocess.check_output(
            ["gcloud", "auth", "print-identity-token"], 
            text=True, 
            stderr=subprocess.PIPE
        ).strip()
        return token
    except subprocess.CalledProcessError as e:
        print(f"❌ Error getting token: {e.stderr}")
        return None
    except FileNotFoundError:
        print("❌ gcloud CLI not found.")
        return None

def trigger_tfl_agent():
    # 1. Setup Argument Parsing
    parser = argparse.ArgumentParser(description="Trigger TfL Agent via REST")
    # Using 'store_true' means if --mail is present, it's True, otherwise False
    parser.add_argument("--mail", action="store_true", help="Trigger the Mail endpoint instead of the App endpoint")
    args = parser.parse_args()

    # 2. Configuration
    APP_URL = "https://tfl-agent-service-682143946483.us-central1.run.app/process-query"
    # Fixed the double slash in the URL you provided
    MAIL_URL = "https://tfl-agent-service-682143946483.us-central1.run.app/trigger-route-check"

    # Select target based on flag
    target_url = MAIL_URL if args.mail else APP_URL
    endpoint_name = "MAIL" if args.mail else "APP (Agent)"

    # 3. Authentication
    token = get_gcloud_identity_token()
    if not token:
        print("🛑 Could not proceed without a valid Identity Token.")
        return

    # 4. Request Payload
    payload = {
        "query": (
            "Find the best 3 routes from Fairlop to Bromley South for tomorrow "
            "departing at 05:45. Apply the delay penalty logic and format the "
            "result for a WhatsApp notification."
        ),
        "subject_line": "TfL Journey: Fairlop to Bromley",
        "recipient": "mmistroni@gmail.com"
    }

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }

    # 5. Execution
    print(f"🚀 Triggering TfL {endpoint_name} endpoint...")
    print(f"🔗 URL: {target_url}")
    
    try:
        response = requests.post(target_url, json=payload, headers=headers)
        
        print(f"HTTP Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print(f"✅ Request successful! Response from {endpoint_name}:")
            # Handle empty responses or non-JSON responses gracefully
            try:
                print(json.dumps(response.json(), indent=2))
            except json.JSONDecodeError:
                print(response.text if response.text else "Success (No body)")
        else:
            print(f"⚠️ Request failed.")
            print(f"Response Body: {response.text}")
            
    except Exception as e:
        print(f"❌ An error occurred during the request: {e}")

if __name__ == "__main__":
    trigger_tfl_agent()