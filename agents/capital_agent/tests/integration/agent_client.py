import os
import json
import asyncio
import sys
from typing import Dict, Any, Optional
from datetime import datetime
import httpx 

# --- Dynamic URL Configuration (for Codespaces internal access) ---
APP_URL = "http://127.0.0.1:8080" 
USER_ID = "user_123"
SESSION_ID = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}" 
APP_NAME = "capital_agent" # Must match your agent's name
# ---------------------------------------

# --- Helper Function: Authentication Bypass ---

async def get_auth_token() -> str:
    """Returns an empty string for local/Codespace unauthenticated development."""
    return ""

# --- Core Request Function (ASYNC) ---

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

        response.raise_for_status() 
        return response
    except httpx.HTTPStatusError as errh:
        print(f"\n❌ **HTTP ERROR:** Status {errh.response.status_code} for {url}")
        print(f"❌ **Server Response (Raw):**\n{errh.response.text}")
        raise
    except httpx.RequestError as err:
        print(f"\n❌ An unexpected network error occurred connecting to {url}: {err}")
        raise

# 📢 AMENDED FUNCTION: Added 'streaming' argument
async def run_agent_request(
    client: httpx.AsyncClient, 
    session_id: str, 
    message: str, 
    streaming: bool = False # Default to False for Pytest/Testability
) -> str:
    """
    Executes a request to the /run_sse endpoint.
    Handles streaming output if requested (for standalone console).
    Returns the final response text.
    """
    
    run_data = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": streaming # 📢 Uses the argument to control streaming
    }
    
    raw_text = ""
    
    try:
        response = await make_request(client, "POST", "/run_sse", data=run_data)
        raw_text = response.text.strip()
        
        # --- ROBUST SSE PARSING LOGIC ---
        
        data_lines = [line.strip() for line in raw_text.split('\n') if line.strip().startswith("data:")]
        
        if not data_lines:
             # Case 1: No 'data:' lines. Try parsing the whole response as a single bare JSON error object.
             try:
                 error_response = json.loads(raw_text)
                 error_message = error_response.get('error', 'Unknown bare JSON error.')
                 return f"SERVER_ERROR: {error_message}"
             except json.JSONDecodeError:
                 return f"PARSING_ERROR: Unexpected non-JSON response from server."


        # 2. Get the very last data block, which contains the final response payload.
        last_data_line = data_lines[-1]
        json_payload = last_data_line[len("data:"):].strip()
        
        agent_response = json.loads(json_payload)
        
        # 3. Extract the final text.
        final_text = agent_response.get('content', {}).get('parts', [{}])[0].get('text', 'Agent response structure not recognized.')
        
        # 📢 STANDALONE/STREAMING OUTPUT: Print if streaming was requested
        if streaming:
             print(f"[Agent] -> {final_text}")

        # ✅ Return the final text for Pytest assertion
        return final_text
    
    except Exception as e:
        print(f"\n❌ FATAL ERROR during run_agent_request: {e}")
        # 📢 CRITICAL: Always return a string for Pytest validation
        return f"CRASH_ERROR: Failed to process request due to {type(e).__name__}"

# --- Interactive Chat Loop (For Standalone Use) ---

async def chat_loop(client: httpx.AsyncClient, session_id: str):
    """Runs the main conversation loop, handling user input asynchronously."""
    print("--- 💬 Start Chatting (Streaming Mode) ---")
    
    while True:
        try:
            # Note: We set streaming=True here for the interactive console experience
            user_input = await asyncio.to_thread(input, f"[{USER_ID}]: ")
            
            if user_input.lower() in ['quit', 'exit']:
                break
                
            if not user_input.strip():
                continue
            
            # 📢 STANDALONE: Call with streaming=True
            await run_agent_request(client, session_id, user_input, streaming=True) 

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
        try:
            await make_request(client, "POST", current_session_endpoint, data=session_data)
            print(f"✅ Session created successfully.")
        except Exception as e:
            print(f"❌ Could not start session. Is the ADK running? Error: {e}")
            return

        # 2. Start the Interactive Loop
        await chat_loop(client, SESSION_ID)
        
        # 3. Cleanup: Delete Session (Best Practice)
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