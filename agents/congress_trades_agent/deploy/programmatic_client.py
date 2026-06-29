import os
import json
import asyncio
from typing import Dict, Any
from datetime import datetime
import httpx 
import sys

# --- Configuration ---
APP_URL = "https://congress-trades-agent-682143946483.us-central1.run.app"
USER_ID = "user_123"
# A persistent session ID ensures your multi-agent conversation history is maintained
SESSION_ID = f"session_{datetime.now().strftime('%Y%m%d%H%M%S')}" 
APP_NAME = "congress_trades_agent"

async def get_auth_token() -> str:
    """Executes 'gcloud auth print-identity-token' asynchronously to fetch credentials."""
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
        raise RuntimeError("gcloud CLI not found. Please ensure Google Cloud CLI is installed and authenticated.")

async def make_request(client: httpx.AsyncClient, method: str, endpoint: str, data: Dict[str, Any] = None) -> httpx.Response:
    """Helper function for authenticated asynchronous requests using httpx."""
    token = await get_auth_token()
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    url = f"{APP_URL}{endpoint}"
    
    if method.upper() == 'POST':
        response = await client.post(url, headers=headers, json=data)
    else:
        raise ValueError(f"Unsupported method: {method}")

    response.raise_for_status() 
    return response

async def run_agent_request(client: httpx.AsyncClient, session_id: str, message: str):
    """Executes a single POST request to the /run_sse endpoint and processes the output blocks."""
    print(f"\n[User] 🚀 Sending Prompt: '{message}'")
    
    run_data = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": False  # ADK still packages response inside SSE data wrappers
    }
    
    try:
        # Technical analysis routines take time; using an extended timeout target
        response = await make_request(client, "POST", "/run_sse", data=run_data)
        raw_text = response.text.strip()
        
        # 1. Fallback: If ADK responds with immediate clear JSON arrays instead of an SSE block
        if not raw_text.startswith("data:"):
            agent_response = json.loads(raw_text)
            final_text = agent_response.get('content', {}).get('parts', [{}])[0].get('text', '')
            print(f"\n[Agent Response]:\n{final_text}")
            return

        # 2. Extract and iterate over individual 'data:' chunks 
        data_lines = [
            line.strip()[5:].strip() # Strip the leading 'data:' prefix safely
            for line in raw_text.split('\n') 
            if line.strip().startswith("data:")
        ]
        
        if not data_lines:
            print("⚠️ Server returned an SSE structural format, but no valid data lines were parsed.")
            return

        print("\n🔍 Parsing Agent execution layers...")
        final_text_content = ""
        
        # Walk backward to find the final text delivery or concatenate message chunks
        for line in reversed(data_lines):
            try:
                payload = json.loads(line)
                
                # Check for standardized ADK structure block
                content_block = payload.get('content', {})
                if content_block and 'parts' in content_block:
                    parts = content_block.get('parts', [{}])
                    text_chunk = parts[0].get('text', '')
                    if text_chunk:
                        final_text_content = text_chunk
                        break
            except json.JSONDecodeError:
                continue

        if final_text_content:
            print(f"\n[Agent Final Recommendation]:\n{final_text_content}")
        else:
            # If standard structure mapping isn't found, dump the raw final data payload safely
            print("\n[Agent Raw Structural Output]:")
            print(data_lines[-1])

    except httpx.HTTPStatusError as e:
        print(f"\n❌ Execution failed on Cloud Run.")
    except Exception as e:
        print(f"\n❌ Client Runtime Error: {e}")

async def amain(message_to_send: str):
    """Main execution orchestrator."""
    print(f"🤖 Initializing Client Pipeline | Session Context: {SESSION_ID}")
    
    # We use an explicit 5-minute timeout window since the agent computes technical indicators 
    async with httpx.AsyncClient(timeout=300.0) as client:
        
        # 1. Warm-up / Create Session
        session_data = {"state": {"preferred_language": "English"}}
        session_endpoint = f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
        
        try:
            await make_request(client, "POST", session_endpoint, data=session_data)
            print("✅ Agent Session Verified.")
        except Exception as e:
            print(f"❌ Failed to instantiate tracking session: {e}")
            return

        # 2. Trigger the Prompt
        print("\n--- 📊 Initiating Analysis Workflow ---")
        await run_agent_request(client, SESSION_ID, message_to_send)
        print("\n--- ✨ Execution Finished ---")

if __name__ == "__main__":
    if sys.version_info < (3, 9):
        print("🚨 Python 3.9+ required.")
        sys.exit(1)
        
    QUERY = "Run a technical analysis for yesterday's stock picks and give me your recommendations"
    asyncio.run(amain(QUERY))