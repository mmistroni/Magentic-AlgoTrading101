import os
import json
import asyncio
import sys
from typing import Dict, Any
from datetime import datetime
import httpx 

# --- Configuration for Local Testing ---
# 📢 Fixed internal URL (use 127.0.0.1 for maximum internal compatibility)
APP_URL = "http://127.0.0.1:8080" 
USER_ID = "user_123"
SESSION_ID = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}" 
APP_NAME = "capital_agent" # 📢 CHANGE THIS to match your actual agent name
# ---------------------------------------

# --- (Other functions like get_auth_token and make_request remain the same) ---

async def get_auth_token() -> str:
    """Returns an empty string for local/Codespace unauthenticated development."""
    return ""

async def make_request(client: httpx.AsyncClient, method: str, endpoint: str, data: Dict[str, Any] = None) -> httpx.Response:
    """Helper function for asynchronous requests."""
    
    headers = {"Content-Type": "application/json"}
    url = f"{APP_URL}{endpoint}"
    
    try:
        if method.upper() == 'POST':
            response = await client.post(url, headers=headers, json=data)
        elif method.upper() == 'DELETE':
             response = await client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        # Check for status codes 4xx or 5xx
        response.raise_for_status() 
        return response
    except httpx.HTTPStatusError as errh:
        print(f"\n❌ **HTTP ERROR:** Status {response.status_code} for {url}")
        print(f"❌ **Server Response (Raw):**\n{response.text}")
        raise
    except httpx.RequestError as err:
        print(f"\n❌ An unexpected network error occurred connecting to {url}: {err}")
        # Print a diagnostic hint
        print("💡 Hint: Did you run 'adk web --port 8080 --host 0.0.0.0' in a separate terminal?")
        raise

async def run_agent_request(client: httpx.AsyncClient, session_id: str, message: str):
    """Executes a single POST request to the /run_sse endpoint and parses the response."""
    
    print(f"\n[User] -> Sending message: '{message}'")
    
    run_data = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": False 
    }
    
    try:
        response = await make_request(client, "POST", "/run_sse", data=run_data)
        
        raw_text = response.text.strip()
        data_lines = [line.strip() for line in raw_text.split('\n') if line.strip().startswith("data:")]
        
        if not data_lines:
             raise ValueError("No 'data:' lines found in response content.")
        
        last_data_line = data_lines[-1]
        json_payload = last_data_line[len("data:"):].strip()
        agent_response = json.loads(json_payload)
        
        final_text = agent_response.get('content', {}).get('parts', [{}])[0].get('text', 'Agent response structure not recognized.')
        
        print(f"[Agent] -> {final_text}")
        return final_text
    
    except json.JSONDecodeError as e:
        print(f"\n🚨 **JSON PARSING FAILED**!")
        print(f"   Error: {e}")
        print("   --- RAW SERVER CONTENT ---")
        print(raw_text)
        print("   --------------------------")
        
    except Exception as e:
        print(f"❌ Agent request failed: {e}")

# --- Interactive Chat Loop and Main Logic (amain) remain the same ---

async def chat_loop(client: httpx.AsyncClient, session_id: str):
    """Runs the main conversation loop, handling user input asynchronously."""
    print("--- 💬 Start Chatting ---")
    print("Type 'quit' or 'exit' to end the session.")
    
    while True:
        try:
            user_input = await asyncio.to_thread(input, f"[{USER_ID}]: ")
            
            if user_input.lower() in ['quit', 'exit']:
                break
                
            if not user_input.strip():
                continue
                
            await run_agent_request(client, session_id, user_input)

        except Exception as e:
            print(f"An unexpected error occurred in the loop: {e}")
            break

async def amain():
    """Main asynchronous function to set up the session and start the loop."""
    print(f"\n🤖 Starting Interactive Client. Target URL: **{APP_URL}**")
    session_data = {"state": {"preferred_language": "English"}}
    current_session_endpoint = f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
    
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. Create Session
        print("\n## 1. Creating Session")
        try:
            await make_request(client, "POST", current_session_endpoint, data=session_data)
            print(f"✅ Session created successfully. Status 200.")
        except Exception as e:
            print(f"❌ Could not start session. Is the ADK running? Error: {e}")
            return

        # 2. Start the Interactive Loop
        await chat_loop(client, SESSION_ID)
        
        # 3. Cleanup: Delete Session (Best Practice)
        print(f"\n## 3. Deleting Session: {SESSION_ID}")
        try:
             await make_request(client, "DELETE", current_session_endpoint)
             print("✅ Session deleted successfully.")
        except Exception as e:
             print(f"⚠️ Warning: Failed to delete session. {e}")


if __name__ == "__main__":
    if sys.version_info < (3, 9):
        print("🚨 ERROR: This script requires Python 3.9+ for asyncio.to_thread.")
        sys.exit(1)
        
    try:
        asyncio.run(amain())
    except Exception as e:
        print(f"FATAL SYSTEM ERROR: {e}")