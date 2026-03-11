import requests
import subprocess
import json

def get_gcloud_identity_token():
    """
    Mimics $(gcloud auth print-identity-token)
    This works in your Codespace because gcloud is already logged in as you.
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
        print("❌ gcloud CLI not found. Please ensure it is installed and in your PATH.")
        return None

def trigger_tfl_agent():
    # 1. Configuration
    APP_URL = "https://tfl-agent-service-682143946483.us-central1.run.app/process-query"
    
    # 2. Authentication
    token = get_gcloud_identity_token()
    if not token:
        print("🛑 Could not proceed without a valid Identity Token.")
        return

    # 3. Request Payload
    # Note: Using your Fairlop-to-Bromley South query logic
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

    # 4. Execution
    print(f"🚀 Triggering TfL Route Check Agent...")
    try:
        response = requests.post(APP_URL, json=payload, headers=headers)
        
        # 5. Output Handling
        print(f"HTTP Status Code: {response.status_code}")
        
        if response.status_code == 200:
            print("✅ Request successful! Response from Agent:")
            print(json.dumps(response.json(), indent=2))
        else:
            print("⚠️ Request failed.")
            print(f"Response Body: {response.text}")
            
    except Exception as e:
        print(f"❌ An error occurred during the request: {e}")

if __name__ == "__main__":
    trigger_tfl_agent()