import os
import json
import asyncio
import logging
from typing import Dict, Any, List
from datetime import datetime
import httpx
import sys
from google.cloud import bigquery

# Configure clean logging output for Cloud Run Operations Suite
logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

# --- Configuration ---
APP_URL = os.environ.get("AGENT_SERVICE_URL", "https://short-selling-agent-service-682143946483.us-central1.run.app")
USER_ID = "automated_cron_job"
APP_NAME = "short_selling_agent"

# BigQuery Destination Details
PROJECT_ID = "datascience-projects"
DATASET_ID = "finviz_blacklist"
TABLE_ID = "daily_recommendations"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"


async def get_auth_token(target_audience: str) -> str:
    """
    Retrieves an OIDC Identity Token. 
    Detects if it's running inside GCP (Metadata Server) or falls back to local gcloud.
    """
    # 1. Attempt to fetch from Google Cloud Metadata Server (Running on Cloud Run)
    try:
        async with httpx.AsyncClient() as client:
            metadata_url = "http://metadata.google.internal/computeMetadata/v1/instance/service-accounts/default/identity"
            headers = {"Metadata-Flavor": "Google"}
            params = {"audience": target_audience}
            
            response = await client.get(metadata_url, headers=headers, params=params, timeout=5.0)
            if response.status_code == 200:
                logger.info("🔑 Successfully retrieved OIDC token from Google Metadata Server.")
                return response.text.strip()
    except Exception:
        # Silently pass to allow local gcloud fallback
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
            raise RuntimeError(f"gcloud identity command failed: {stderr.decode().strip()}")
            
        logger.info("🔑 Successfully retrieved identity token from local gcloud CLI.")
        return stdout.decode().strip()
    except FileNotFoundError:
        raise RuntimeError("GCP Authentication failed. No local gcloud CLI found and Metadata Server is unreachable.")


async def make_request(client: httpx.AsyncClient, method: str, endpoint: str, data: Dict[str, Any] = None) -> httpx.Response:
    """Helper function for authenticated asynchronous requests using dynamic tokens."""
    token = await get_auth_token(APP_URL)
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
            raise ValueError(f"Unsupported HTTP method: {method}")

        response.raise_for_status() 
        return response
    except httpx.HTTPStatusError as err:
        logger.error(f"❌ HTTP Error {response.status_code} for {url}\nResponse: {response.text}")
        raise err
    except httpx.RequestError as err:
        logger.error(f"❌ Connection Request error: {err}")
        raise err


async def run_agent_request(client: httpx.AsyncClient, session_id: str, message: str) -> List[Dict[str, Any]]:
    """Executes a single POST request to the /run_sse endpoint and parses the final SSE chunk."""
    logger.info(f"💬 Prompting agent via Web API endpoint: '{message}'")
    
    run_data = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": False 
    }
    
    response = await make_request(client, "POST", "/run_sse", data=run_data)
    raw_text = response.text.strip()
    
    # Extract line blocks matching standard Server-Sent Events (SSE) data format
    data_lines = [
        line.strip() 
        for line in raw_text.split('\n') 
        if line.strip().startswith("data:")
    ]
    
    if not data_lines:
         raise json.JSONDecodeError("No SSE data chunks found in the server response.", raw_text, 0)
    
    # Parse the final message block containing complete finalized result payload
    last_data_line = data_lines[-1]
    json_payload = last_data_line[len("data:"):].strip()
    agent_response = json.loads(json_payload)
    
    # Locate final structured candidate output text
    final_text = agent_response.get('content', {}).get('parts', [{}])[0].get('text', '')
    if not final_text:
        raise ValueError("Agent response structure did not contain expected text contents.")
        
    # Unpack potential LLM markdown decorations
    if final_text.startswith("```"):
        lines = final_text.split("\n")
        if lines[0].startswith("