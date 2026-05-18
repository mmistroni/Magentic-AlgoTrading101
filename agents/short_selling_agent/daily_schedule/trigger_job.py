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
        
    # Unpack potential LLM markdown decorations safely
    clean_text = final_text.strip()
    if clean_text.startswith("```"):
        # Remove top backticks line (e.g., ```json or ```)
        lines = clean_text.splitlines()
        if lines[0].startswith("```"):
            lines = lines[1:]
        # Remove trailing backticks line
        if lines and lines[-1].startswith("```"):
            lines = lines[:-1]
        clean_text = "\n".join(lines).strip()
        
    try:
        parsed_data = json.loads(clean_text)
        # Ensure result is formatted as a structured list of JSON rows
        return parsed_data if isinstance(parsed_data, list) else [parsed_data]
    except json.JSONDecodeError as err:
        logger.error(f"❌ Failed to parse processed LLM block into valid JSON structures: {clean_text}")
        raise err


async def main():
    logger.info("🎬 --- STARTING AUTOMATED SHORT-SELLING AGENT CALL ---")
    
    # Generate unique session matching the current calendar batch date
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    session_id = f"session_batch_{today_str}"
    
    bq_client = bigquery.Client(project=PROJECT_ID)
    
    # Query today's exact tickers from the daily losers table
    query = f"""
        SELECT ticker 
        FROM `{PROJECT_ID}.{DATASET_ID}.fmp_daily_losers` 
        WHERE scrape_date = '{today_str}'
    """
    
    try:
        query_job = bq_client.query(query)
        tickers = [row.ticker for row in query_job.result()]
        
        if not tickers:
            logger.warning(f"⚠️ No candidates found in fmp_daily_losers table for date {today_str}. Stopping execution.")
            sys.exit(0)
            
        logger.info(f"📊 Found {len(tickers)} candidates to scan today: {tickers}")
        
        # Build prompt listing specific candidates for the scanning agent
        tickers_payload = ", ".join(tickers)
        prompt_message = (
            f"Run short-selling scans for the following candidates: {tickers_payload}. "
            "Evaluate fundamentals, technical trends, insider activity, and output the final rows "
            "matching your clean output JSON schema format."
        )
        
        async with httpx.AsyncClient(timeout=600.0) as client:
            # 1. Trigger the agent call
            recommendations = await run_agent_request(client, session_id, prompt_message)
            
            # 2. Append standard timestamp track fields to each row
            for row in recommendations:
                row["scan_date"] = today_str
                row["created_at"] = datetime.utcnow().isoformat()
            
            # 3. Stream data output straight into your BigQuery storage table
            logger.info(f"📤 Streaming {len(recommendations)} evaluation logs into BigQuery: {TABLE_REF}")
            errors = bq_client.insert_rows_json(TABLE_REF, recommendations)
            
            if errors:
                logger.error(f"❌ BigQuery Write Exceptions occurred: {errors}")
                sys.exit(1)
            else:
                logger.info("🎉 SUCCESS: Short-selling agent decisions successfully committed to BigQuery.")
                
            # 4. Clean up old conversational memory state for the next run
            logger.info("🧹 Sweeping session conversational logs to keep memory state pristine...")
            await make_request(client, "DELETE", f"/history/{APP_NAME}/{USER_ID}/{session_id}")
            logger.info("✨ Cleanup complete.")
            
    except Exception as e:
        logger.error(f"💥 Fatal pipeline execution failure: {e}", exc_info=True)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())