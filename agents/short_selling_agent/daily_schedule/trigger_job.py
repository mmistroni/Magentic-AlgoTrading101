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
    print("🔑 [AUTH] Attempting to acquire OIDC token...")
    # 1. Attempt to fetch from Google Cloud Metadata Server (When running live on Cloud Run)
    try:
        async with httpx.AsyncClient() as client:
            metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
            headers = {"Metadata-Flavor": "Google"}
            params = {"audience": APP_URL}
            
            response = await client.get(metadata_url, headers=headers, params=params, timeout=5.0)
            if response.status_code == 200:
                print("✅ [AUTH] Token successfully acquired via GCP Metadata Server.")
                return response.text.strip()
    except Exception as e:
        print(f"ℹ️ [AUTH] Metadata Server approach skipped or failed: {e}")

    # 2. Fallback: Run 'gcloud auth print-identity-token' (Local Codespaces Run)
    try:
        print("ℹ️ [AUTH] Falling back to local gcloud CLI token extraction...")
        proc = await asyncio.create_subprocess_exec(
            "gcloud", "auth", "print-identity-token",
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await proc.communicate()
        
        if proc.returncode != 0:
            raise RuntimeError(f"gcloud command failed: {stderr.decode().strip()}")
            
        print("✅ [AUTH] Token successfully acquired via gcloud CLI fallback.")
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
    print(f"📡 [NETWORK] Dispatching {method.upper()} request to: {url}")
    
    try:
        if method.upper() == 'POST':
            response = await client.post(url, headers=headers, json=data)
        elif method.upper() == 'DELETE':
             response = await client.delete(url, headers=headers)
        else:
            raise ValueError(f"Unsupported method: {method}")

        print(f"📡 [NETWORK] Received status code {response.status_code} from server.")
        response.raise_for_status() 
        return response
    except httpx.HTTPStatusError as errh:
        print(f"\n❌ **HTTP ERROR:** Status {response.status_code} for {url}")
        print(f"❌ **Server Response (Raw text layout):**\n{response.text}")
        raise
    except httpx.RequestError as err:
        print(f"\n❌ An unexpected network request error occurred: {err}")
        raise

async def run_agent_request(client: httpx.AsyncClient, session_id: str, message: str) -> str:
    """
    Executes a single POST request to the unary /run endpoint.
    Bypasses chunked proxy streaming completely to protect message content delivery.
    """
    print(f"\n[User] -> Sending request to Unary Endpoint: '{message}'")
    
    run_data = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": False 
    }
    
    response = await make_request(client, "POST", "/run", data=run_data)
    
    print("\n==================== 📥 RAW UNARY RESPONSE FROM SERVER ====================")
    print(response.text)
    print("===========================================================================\n")
    
    try:
        agent_response = response.json()
    except Exception as parse_err:
        print(f"❌ [PARSING] Failed parsing core wrapper JSON response dictionary payload: {parse_err}")
        raise json.JSONDecodeError("Failed to parse standard Unary JSON response structure.", response.text, 0)
    
    # Extract final text block cleanly from the structural model schema payload
    final_text = agent_response.get('content', {}).get('parts', [{}])[0].get('text', '')
    
    if not final_text:
        print("⚠️ [PARSING] Warning: The 'text' block inside content.parts[0] was empty or missing.")
        final_text = 'Agent response structural text element was returned empty.'
        
    print("\n==================== 📑 EXTRACTED CLEAN AGENT TEXT STRING ====================")
    print(final_text)
    print("==============================================================================\n")
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
            print(f"✅ Session state re-initialized successfully.")
        except Exception as e:
            print(f"❌ Could not start session framework: {e}")
            return

        # 2. Run Single Request & Capture Output Text
        print(f"--- 💬 Executing Single Task ---")
        agent_text = ""
        try:
            agent_text = await run_agent_request(client, SESSION_ID, message_to_send)
            print(f"✅ [Agent] -> Raw Response Captured successfully.")
        except Exception as e:
            print(f"❌ Agent execution runtime error: {e}")
            return
        
        # 3. Parse Text Responses and Stream directly to BigQuery
        if agent_text:
            clean_text = agent_text.strip()
            # Clean off any potential markdown wrappers if the agent wrapped its JSON block
            if clean_text.startswith("```"):
                print("✂️ [PARSING] Detected Markdown block fences. Stripping wrappers out...")
                lines = clean_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()
                
            try:
                print("🔍 [PARSING] Attempting to deserialize clean text block into JSON...")
                parsed_json = json.loads(clean_text)
                
                # Double check if it's nested inside a 'final_decisions' wrapper dict element
                if isinstance(parsed_json, dict) and "final_decisions" in parsed_json:
                    print("📂 [PARSING] Detected 'final_decisions' nesting key object. Slicing inner array data...")
                    raw_rows = parsed_json["final_decisions"]
                else:
                    raw_rows = parsed_json if isinstance(parsed_json, list) else [parsed_json]
                
                print(f"📊 [PARSING] Discovered {len(raw_rows)} individual target asset evaluation rows inside data payload.")
                
                rows_to_insert = []
                today_str = datetime.utcnow().strftime('%Y-%m-%d')
                timestamp_now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f UTC')

                print("\n==================== 🛠️ COMPILING ROWS FOR BIGQUERY ====================")
                for index, row in enumerate(raw_rows):
                    compiled_row = {
                        "evaluation_date": row.get("evaluation_date", today_str),
                        "ticker": str(row.get("ticker", "")).upper(),
                        "conviction_score": int(row.get("conviction_score", 3)),
                        "action": str(row.get("action", "WATCH")).upper(),
                        "reasoning": row.get("reasoning", None),
                        "inserted_at": timestamp_now
                    }
                    print(f"👉 Row [{index}] Compiled Payload Architecture:")
                    print(json.dumps(compiled_row, indent=2))
                    rows_to_insert.append(compiled_row)
                print("==========================================================================\n")
                
                if rows_to_insert:
                    print(f"📤 [BIGQUERY] Initializing streaming upload framework target connection: {TABLE_REF}")
                    bq_client = bigquery.Client(project=PROJECT_ID)
                    
                    print(f"📤 [BIGQUERY] Broadcasting packet chunk array ({len(rows_to_insert)} items) via streaming API call...")
                    errors = bq_client.insert_rows_json(TABLE_REF, rows_to_insert)
                    
                    if errors:
                        print("\n❌ ==================== 🔥 BIGQUERY INSERT ERRORS OCCURRED ====================")
                        print(json.dumps(errors, indent=2))
                        print("=================================================================================\n")
                    else:
                        print("🎉 ==================== 🚀 SUCCESSFUL BIGQUERY INGESTION ====================")
                        print(f" All {len(rows_to_insert)} items successfully appended to BigQuery storage layer.")
                        print("===============================================================================\n")
                else:
                    print("⚠️ [BIGQUERY] Aborting ingestion phase: No rows were successfully extracted or compiled.")
                        
            except json.JSONDecodeError as decode_error:
                print("\n🚨 ==================== 💥 JSON PARSE ERROR OCCURRED ====================")
                print(f"Message: Agent did not output a cleanly parsable JSON data block schema structure.")
                print(f"Exception Track: {decode_error}")
                print(f"--- RAW BLOCK INGESTION STRIPPED SOURCE ---\n{clean_text}")
                print("============================================================================\n")
            except Exception as bq_err:
                print(f"❌ [BIGQUERY] Failed to complete execution or compile transaction context: {bq_err}")

        # 4. Cleanup: Delete Session
        await asyncio.sleep(1) 
        print(f"\n## 3. Deleting active processing Session Context: {SESSION_ID}")
        try:
            await make_request(client, "DELETE", current_session_endpoint)
            print("✅ Session state torn down cleanly.")
        except Exception as e:
            print(f"⚠️ Warning: Failed to clear tracking frame out completely. {e}")

if __name__ == "__main__":
    if sys.version_info < (3, 9):
        print("🚨 ERROR: Python 3.9+ required.")
        sys.exit(1)
        
    # Dynamically pick up today's date string (e.g., "2026-05-30")
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    QUERY = f"Run the short-selling pipeline for {today_str}."
    
    try:
        asyncio.run(amain(QUERY))
    except Exception as e:
        print(f"FATAL SYSTEM FAILURE EXECUTION TRACE: {e}")