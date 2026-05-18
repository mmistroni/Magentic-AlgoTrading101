import os
import json
import subprocess
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import httpx 
import sys
from google.cloud import bigquery

# --- Configuration (Dynamic) ---
APP_URL = os.environ.get("AGENT_SERVICE_URL", "https://short-selling-agent-service-682143946483.us-central1.run.app")
USER_ID = "automated_cron_job"
SESSION_ID = f"session_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}" 
APP_NAME = "short_selling_agent"

# BigQuery Destination Schema Configuration
PROJECT_ID = "datascience-projects"
DATASET_ID = "finviz_blacklist"
TABLE_ID = "daily_recommendations"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"

# --- Authentication Function (ASYNC) ---

async def get_auth_token() -> str:
    """
    Retrieves an OIDC Identity Token. 
    Detects if it's running inside GCP (Metadata Server) or falls back to local gcloud.
    """
    # 1. Attempt to fetch from Google Cloud Metadata Server (When running live on Cloud Run)
    try:
        async with httpx.AsyncClient() as client:
            metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
            headers = {"Metadata-Flavor": "Google"}
            params = {"audience": APP_URL}
            
            response = await client.get(metadata_url, headers=headers, params=params, timeout=5.0)
            if response.status_code == 200:
                return response.text.strip()
    except Exception:
        pass

    # 2. Fallback: Run 'gcloud auth print-identity-token' (Local Codespaces Run)
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

async def run_agent_request(client: httpx.AsyncClient, session_id: str, message: str) -> str:
    """Executes a single POST request to the /run_sse endpoint and returns the raw agent text string."""
    print(f"\n[User] -> Sending message: '{message}'")
    
    run_data = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": False 
    }
    
    response = await make_request(client, "POST", "/run_sse", data=run_data)
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
    return final_text

# --- Main Logic (ASYNC) ---

async def amain(message_to_send: str):
    """Main function to run a single interaction, parse recommendations, insert into BigQuery, and then cleanup."""
    print(f"\n🤖 Starting Single-Run Client | Session: **{SESSION_ID}**")
    
    session_data = {"state": {"preferred_language": "English", "visit_count": 5}}
    current_session_endpoint = f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
    
    async with httpx.AsyncClient(timeout=600.0) as client: # Generous timeout for deep agent analytics
        
        # 1. Create Session
        try:
            await make_request(client, "POST", current_session_endpoint, data=session_data)
            print(f"✅ Session created.")
        except Exception as e:
            print(f"❌ Could not start session: {e}")
            return

        # 2. Run Single Request & Capture Output Text
        print(f"--- 💬 Executing Single Task ---")
        agent_text = ""
        try:
            agent_text = await run_agent_request(client, SESSION_ID, message_to_send)
            print(f"[Agent] -> Raw Response Captured.")
        except Exception as e:
            print(f"❌ Agent execution error: {e}")
            return
        
        # 3. Parse Text Responses and Stream directly to BigQuery
        if agent_text:
            clean_text = agent_text.strip()
            # Clean off any potential markdown wrappers if the agent wrapped its JSON block
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()
                
            try:
                # Expecting the agent output to be a list of dicts, or a single dict object
                parsed_json = json.loads(clean_text)
                raw_rows = parsed_json if isinstance(parsed_json, list) else [parsed_json]
                
                rows_to_insert = []
                today_str = datetime.utcnow().strftime('%Y-%m-%d')
                timestamp_now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f UTC')

                for row in raw_rows:
                    # Enforce exact BigQuery column mappings and data schema requirements
                    rows_to_insert.append({
                        "evaluation_date": row.get("evaluation_date", today_str),
                        "ticker": str(row.get("ticker", "")).upper(),
                        "conviction_score": int(row.get("conviction_score", 3)),
                        "action": str(row.get("action", "WATCH")).upper(),
                        "reasoning": row.get("reasoning", None),
                        "inserted_at": timestamp_now
                    })
                
                if rows_to_insert:
                    print(f"📤 Streaming {len(rows_to_insert)} records to BigQuery table: {TABLE_REF}")
                    bq_client = bigquery.Client(project=PROJECT_ID)
                    errors = bq_client.insert_rows_json(TABLE_REF, rows_to_insert)
                    
                    if errors:
                        print(f"❌ BigQuery Insert Errors occurred: {errors}")
                    else:
                        print("🎉 SUCCESS: All items parsed and recorded in BigQuery table.")
                        
            except json.JSONDecodeError:
                print("🚨 Parse Error: Agent did not output a clean, parsable structured JSON response string.")
                print(f"--- RAW UNPARSABLE TEXT ---\n{agent_text}\n---------------------------")
            except Exception as bq_err:
                print(f"❌ Failed to successfully compile or upload data to BigQuery: {bq_err}")

        # 4. Cleanup: Delete Session
        await asyncio.sleep(1) 
        print(f"\n## 3. Deleting Session: {SESSION_ID}")
        try:
            await make_request(client, "DELETE", current_session_endpoint)
            print("✅ Session deleted successfully.")
        except Exception as e:
            print(f"⚠️ Warning: Failed to delete session. {e}")

if __name__ == "__main__":
    if sys.version_info < (3, 9):
        print("🚨 ERROR: Python 3.9+ required.")
        sys.exit(1)
        
    # Dynamically pick up today's date string (e.g., "2026-05-18")
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    QUERY = f"Run the short-selling pipeline for {today_str}."
    
    try:
        asyncio.run(amain(QUERY))
    except Exception as e:
        print(f"FATAL ERROR: {e}")