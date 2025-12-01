import os
import json
import subprocess
import asyncio
from typing import Dict, Any
from datetime import datetime
import httpx 
import sys # ⬅️ ADDED: sys module for version check

# --- Configuration (Dynamic) ---
APP_URL = "https://multi-agent-service-682143946483.us-central1.run.app"
USER_ID = "user_123"
# Generate a single session ID for the entire conversation loop
SESSION_ID = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}" 
APP_NAME = "multi_agent"

# --- Authentication Function (ASYNC) ---

async def get_auth_token() -> str:
    """
    Executes 'gcloud auth print-identity-token' asynchronously to get the token.
    """
    try:
        proc = await asyncio.create_subprocess_exec(
            "gcloud", "auth", "print-identity-token",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"gcloud command failed: {stderr.decode().strip()}")
            
        return stdout.decode().strip()
    except FileNotFoundError:
        raise RuntimeError("gcloud command not found. Please ensure Google Cloud CLI is installed.")

# --- API Interaction Functions (ASYNC) ---

async def make_request(client: httpx.AsyncClient, method: str, endpoint: str, data: Dict[str, Any] = None) -> httpx.Response:
    """Helper function for authenticated asynchronous requests using httpx."""
    token = await get_auth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    url = f"{APP_URL}{endpoint}"
    
    try:
        if method.upper() == 'POST':
            response = await client.post(url, headers=headers, json=data)
        elif method.upper() == 'DELETE':
             response = await client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        response.raise_for_status() 
        return response
    except httpx.HTTPStatusError as errh:
        print(f"\n❌ **HTTP ERROR:** Status {response.status_code} for {url}")
        print(f"❌ **Server Response (Raw):**\n{response.text}")
        raise
    except httpx.RequestError as err:
        print(f"\n❌ An unexpected request error occurred: {err}")
        raise

async def run_agent_request(client: httpx.AsyncClient, session_id: str, message: str):
    """Executes a single POST request to the /run_sse endpoint."""
    
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
        current_status = response.status_code
        # print(f"**Request Status Code:** {current_status}") 

        raw_text = response.text.strip()
        
        # Multi-line SSE parsing logic
        data_lines = [
            line.strip() 
            for line in raw_text.split('\n') 
            if line.strip().startswith("data:")
        ]
        
        if not data_lines:
             raise json.JSONDecodeError("No 'data:' lines found in 200 response.", raw_text, 0)
        
        last_data_line = data_lines[-1]
        json_payload = last_data_line[len("data:"):].strip()
        agent_response = json.loads(json_payload)
        
        # Extract the final text 
        final_text = agent_response.get('content', {}).get('parts', [{}])[0].get('text', 'Agent response structure not recognized.')
        
        print(f"[Agent] -> {final_text}")
    
    except json.JSONDecodeError as e:
        print(f"\n🚨 **JSON PARSING FAILED**!")
        print(f"   Error: {e}")
        print("   --- RAW SERVER CONTENT ---")
        print(raw_text)
        print("   --------------------------")
        
    except Exception as e:
        print(f"❌ Agent request failed: {e}")

# --- Interactive Chat Loop ---

async def chat_loop(client: httpx.AsyncClient, session_id: str):
    """Runs the main conversation loop, handling user input asynchronously."""
    print("--- 💬 Start Chatting ---")
    print("Type 'quit' or 'exit' to end the session.")
    
    while True:
        try:
            # Use asyncio.to_thread to run blocking input() without freezing the event loop
            user_input = await asyncio.to_thread(input, f"[{USER_ID}]: ")
            
            if user_input.lower() in ['quit', 'exit']:
                break
                
            if not user_input.strip():
                continue
                
            # Send the message to the agent
            await run_agent_request(client, session_id, user_input)

        except Exception as e:
            print(f"An unexpected error occurred in the loop: {e}")
            break

# --- Main Logic (ASYNC) ---

async def amain():
    """Main asynchronous function to set up the session and start the loop."""
    print(f"\n🤖 Starting Interactive Client with Session ID: **{SESSION_ID}**")
    session_data = {"state": {"preferred_language": "English", "visit_count": 5}}
    current_session_endpoint = f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
    
    # httpx.AsyncClient is used as a context manager to manage connections
    async with httpx.AsyncClient(timeout=30.0) as client:
        
        # 1. Create Session
        print("\n## 1. Creating Session")
        try:
            await make_request(client, "POST", current_session_endpoint, data=session_data)
            print(f"✅ Session created successfully. Status 200.")
        except Exception as e:
            print(f"❌ Could not start session: {e}")
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
    # Check for Python version as asyncio.to_thread is Python 3.9+
    if sys.version_info < (3, 9):
        print("🚨 ERROR: This script requires Python 3.9+ for asyncio.to_thread.")
        sys.exit(1)
        
    try:
        asyncio.run(amain())
    except RuntimeError as e:
        print(f"FATAL ASYNC ERROR: {e}")