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

# BigQuery Source Details
PROJECT_ID = "datascience-projects"
DATASET_ID = "finviz_blacklist"
TABLE_ID = "fmp_daily_losers"

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

async def run_agent_request(client: httpx.AsyncClient, session_id: str, message: str):
    """Executes a single POST request to the /run_sse endpoint and parses output chunks."""
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

# --- BigQuery Ticker Extractor ---

def get_tickers_from_bigquery(today_str: str) -> List[str]:
    """Queries the daily losers table for tickers corresponding to the given date."""
    print(f"🔍 Querying BigQuery for losers tracked on: {today_str}")
    bq_client = bigquery.Client(project=PROJECT_ID)
    
    query = f"""
        SELECT ticker 
        FROM `{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}` 
        WHERE scrape_date = '{today_str}'
    """
    query_job = bq_client.query(query)
    results = query_job.result()
    return [row.ticker for row in results]

# --- Main Logic (ASYNC) ---

async def amain():
    """Main function to query tickers, run a single interaction, and clean up."""
    print(f"\n🤖 Starting Automated Ingestion Trigger | Session: **{SESSION_ID}**")
    
    # 1. Fetch Today's Date and Tickers
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    try:
        tickers = get_tickers_from_bigquery(today_str)
        if not tickers:
            print(f"⚠️ No tickers found in BigQuery for date {today_str}. Exiting gracefully.")
            return
        print(f"📊 Found {len(tickers)} candidates to scan today: {tickers}")
    except Exception as e:
        print(f"❌ Failed to fetch tickers from BigQuery: {e}")
        sys.exit(1)

    # 2. Build the dynamic pipeline query string
    tickers_payload = ", ".join(tickers)
    query_message = (
        f"Run short-selling scans for the following candidates: {tickers_payload}. "
        "Evaluate fundamentals, technical trends, and insider activity."
    )

    session_data = {"state": {"preferred_language": "English", "visit_count": 1}}
    current_session_endpoint = f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
    
    async with httpx.AsyncClient(timeout=600.0) as client: # Large timeout for deep agent analytics
        
        # 3. Create Session
        try:
            await make_request(client, "POST", current_session_endpoint, data=session_data)
            print(f"✅ Session created.")
        except Exception as e:
            print(f"❌ Could not start session: {e}")
            return

        # 4. Run Request with dynamically pulled tickers
        print(f"--- 💬 Executing Pipeline Scan ---")
        try:
            await run_agent_request(client, SESSION_ID, query_message)
        except Exception as e:
            print(f"❌ Agent execution error: {e}")
        
        # 5. Cleanup: Delete Session
        await asyncio.sleep(1) 
        print(f"\n## Deleting Session: {SESSION_ID}")
        try:
            await make_request(client, "DELETE", current_session_endpoint)
            print("✅ Session deleted successfully.")
        except Exception as e:
            print(f"⚠️ Warning: Failed to delete session. {e}")

if __name__ == "__main__":
    if sys.version_info < (3, 9):
        print("🚨 ERROR: Python 3.9+ required.")
        sys.exit(1)
        
    try:
        asyncio.run(amain())
    except Exception as e:
        print(f"FATAL ERROR: {e}")