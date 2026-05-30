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
    print(f"\n🤖 Starting Single