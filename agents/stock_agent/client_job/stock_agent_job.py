import os
import json
import asyncio
from typing import Dict, Any, List
from datetime import datetime, timedelta
import httpx 
import sys
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from google.cloud import bigquery

# --- Configuration (Stock Agent & BigQuery Target) ---
APP_URL = os.environ.get("AGENT_SERVICE_URL", "https://stock-agent-service-682143946483.us-central1.run.app")
USER_ID = "automated_cron_job"
SESSION_ID = f"session_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}" 
APP_NAME = "stock_agent"

# Reusing the existing Short-Selling Agent destination table
PROJECT_ID = os.environ.get("GCP_PROJECT", "datascience-projects")
DATASET_ID = "finviz_blacklist"
TABLE_ID = "daily_recommendations"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"


# --- EMAIL NOTIFICATION LAYER (GMAIL SMTP) ---

def send_strategy_report(subject: str, html_body: str):
    """
    Synchronous worker that dispatches an HTML report directly via Gmail SMTP using EMAIL_PASSWORD.
    """
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    PRIMARY_EMAIL = "mmistroni@gmail.com"
    APP_PASSWORD = os.getenv("EMAIL_PASSWORD").replace(" ", "")

    if not APP_PASSWORD:
        print("⚠️ [EMAIL] EMAIL_PASSWORD environment variable is not set! Skipping email dispatch.")
        return

    msg = MIMEMultipart("alternative")
    msg['From'] = PRIMARY_EMAIL
    msg['To'] = PRIMARY_EMAIL
    msg['Subject'] = subject

    msg.attach(MIMEText(html_body, 'html'))

    try:
        print(f"📤 [EMAIL] Transmitting report to {PRIMARY_EMAIL} via Gmail SMTP...")
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()
            server.login(PRIMARY_EMAIL, APP_PASSWORD)
            server.sendmail(PRIMARY_EMAIL, PRIMARY_EMAIL, msg.as_string())
        print("📨 [EMAIL] Report sent successfully via Gmail SMTP!")
    except Exception as e:
        print(f"❌ [EMAIL] Fail. FAiled again.Failed to send email via SMTP: {e} for {PRIMARY_EMAIL}/{APP_PASSWORD}")


def build_summary_email_and_send(rows_inserted: List[Dict[str, Any]], target_date_str: str):
    """Constructs a responsive HTML summary dashboard and triggers Gmail SMTP dispatch."""
    print('============= GENERATING OPERATIONAL SUMMARY EMAIL =============')

    if not rows_inserted:
        subject_str = f"Stock Agent Operations Report - {target_date_str} [EMPTY]"
        display_content = """
        <div style="padding: 15px; background-color: #fdfefe; border: 1px solid #e2e8f0; border-left: 4px solid #94a3b8; border-radius: 4px;">
            <p style="margin: 0; font-size: 14px; color: #334155; font-weight: bold;">
                No trade candidates or signals were generated for this market snapshot date.
            </p>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #64748b;">
                The execution pipeline finalized checks successfully with zero output records.
            </p>
        </div>
        """
    else:
        subject_str = f"Stock Agent Operations Report - {target_date_str} | {len(rows_inserted)} Signals"
        table_rows = ""
        for r in rows_inserted:
            action = str(r.get("action", "HOLD")).upper()
            
            if action in ["BUY", "LONG"]:
                bg_color = "#e6f7e9"
                text_color = "#1e5a2c"
            elif action in ["SELL", "SHORT"]:
                bg_color = "#ffe6eb"
                text_color = "#cc0033"
            else:  # HOLD / AVOID
                bg_color = "#f8f9fa"
                text_color = "#495057"

            score = r.get("conviction_score", 0)

            table_rows += f"""
            <tr style="background-color: {bg_color}; color: {text_color}; font-size: 13px;">
                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{r.get('ticker', 'N/A')}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold;">{action}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{score}</td>
                <td style="padding: 10px; border: 1px solid #ddd; line-height: 1.4;">{r.get('reasoning', 'N/A')}</td>
            </tr>
            """

        display_content = f"""
        <table style="width: 100%; border-collapse: collapse; min-width: 500px;">
            <thead>
                <tr style="background-color: #1a365d; color: white; text-align: left;">
                    <th style="padding: 12px; border: 1px solid #ddd;">Ticker</th>
                    <th style="padding: 12px; border: 1px solid #ddd; text-align: center;">Action</th>
                    <th style="padding: 12px; border: 1px solid #ddd; text-align: center;">Conviction Score</th>
                    <th style="padding: 12px; border: 1px solid #ddd;">Analytical Reasoning</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        """

    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333333; margin: 20px;">
        <h2 style="color: #1a365d; border-bottom: 2px solid #1a365d; padding-bottom: 10px; font-size: 20px;">
            Stock Agent Pipeline Execution Summary
        </h2>
        <p style="font-size: 13px; margin: 4px 0;"><strong>Snapshot Target Date:</strong> {target_date_str}</p>
        <p style="font-size: 13px; margin: 4px 0;"><strong>Session ID:</strong> <code>{SESSION_ID}</code></p>
        <br>
        {display_content}
        <br>
        <p style="font-size: 11px; color: #7f8c8d; border-top: 1px solid #eeeeee; padding-top: 10px;">
            Automated Quantitative Signal • Stock Agent Cloud Run Job
        </p>
    </body>
    </html>
    """

    send_strategy_report(subject_str, html_content)


# --- AUTHENTICATION LAYER (ASYNC) ---

async def get_auth_token() -> str:
    """Retrieves an OIDC Identity Token for authenticating against Cloud Run."""
    print("🔑 [AUTH] Attempting to acquire OIDC token...")
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
        print(f"ℹ️ [AUTH] Metadata Server approach skipped: {e}")

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


# --- API INTERACTION LAYER (ASYNC) ---

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
        print(f"\n❌ HTTP ERROR Status {errh.response.status_code} for {url}")
        print(f"❌ Server Response:\n{errh.response.text}")
        raise
    except httpx.RequestError as err:
        print(f"\n❌ Network request error occurred: {err}")
        raise


async def run_agent_request(client: httpx.AsyncClient, session_id: str, message: str) -> str:
    """Executes a single POST request to the unary /run endpoint."""
    print(f"\n[User] -> Sending request to Unary Endpoint: '{message}'")
    
    run_data = {
        "app_name": APP_NAME,
        "user_id": USER_ID,
        "session_id": session_id,
        "new_message": {"role": "user", "parts": [{"text": message}]},
        "streaming": False 
    }
    
    response = await make_request(client, "POST", "/run", data=run_data)
    
    try:
        agent_response = response.json()
    except Exception as parse_err:
        print(f"❌ [PARSING] Failed parsing core JSON payload: {parse_err}")
        raise json.JSONDecodeError("Failed to parse standard Unary JSON response structure.", response.text, 0)
    
    target_payload = agent_response
    if isinstance(agent_response, list):
        if not agent_response:
            return 'Agent response structural text element was returned empty.'
        target_payload = agent_response[-1]

    if isinstance(target_payload, dict):
        final_text = target_payload.get('content', {}).get('parts', [{}])[0].get('text', '')
    else:
        final_text = str(target_payload)
    
    if not final_text:
        final_text = 'Agent response structural text element was returned empty.'
        
    print("\n==================== EXTRACTED AGENT TEXT OUTPUT ====================")
    print(final_text)
    print("======================================================================\n")
    return final_text


# --- MAIN PIPELINE EXECUTION ---

async def amain(message_to_send: str, target_date_str: str):
    """Main execution orchestrator."""
    print(f"\n🤖 Starting Single-Run Stock Job | Session: **{SESSION_ID}** | Snapshot Date: **{target_date_str}**")
    
    session_data = {"state": {}}
    current_session_endpoint = f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
    
    async with httpx.AsyncClient(timeout=600.0) as client:
        
        # 1. Initialize Session Context
        try:
            await make_request(client, "POST", current_session_endpoint, data=session_data)
            print(f"✅ Session state re-initialized successfully.")
        except Exception as e:
            print(f"❌ Could not start session framework: {e}")
            return

        # 2. Run Task and Extract Output
        agent_text = ""
        try:
            agent_text = await run_agent_request(client, SESSION_ID, message_to_send)
        except Exception as e:
            print(f"❌ Agent execution error: {e}")
            return
        
        # 3. Parse JSON & Upload to BigQuery
        if agent_text:
            loop = asyncio.get_running_loop()
            clean_text = agent_text.strip()
            
            # Remove Markdown code blocks if present
            if clean_text.startswith("```"):
                lines = clean_text.splitlines()
                if lines[0].startswith("```"):
                    lines = lines[1:]
                if lines and lines[-1].startswith("```"):
                    lines = lines[:-1]
                clean_text = "\n".join(lines).strip()
                
            rows_to_insert = []
            try:
                print("🔍 [PARSING] Attempting to deserialize clean text block into JSON...")
                parsed_json = json.loads(clean_text)
                
                if isinstance(parsed_json, dict) and "signals" in parsed_json:
                    raw_rows = parsed_json["signals"]
                else:
                    raw_rows = parsed_json if isinstance(parsed_json, list) else [parsed_json]
                
                timestamp_now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f UTC')

                for index, row in enumerate(raw_rows):
                    ticker_upper = str(row.get("ticker", "UNKNOWN")).upper()
                    
                    # Map signals to match finviz_blacklist.daily_recommendations schema
                    action_val = str(row.get("signal", row.get("action", "HOLD"))).upper()
                    raw_score = row.get("confidence_score", row.get("conviction_score", 3))
                    
                    compiled_row = {
                        "evaluation_date": target_date_str,
                        "ticker": ticker_upper,
                        "conviction_score": int(float(raw_score)),
                        "action": action_val,
                        "reasoning": row.get("reasoning", "No detailed reasoning provided."),
                        "inserted_at": timestamp_now
                    }
                    rows_to_insert.append(compiled_row)

                if rows_to_insert:
                    print(f"📤 [BIGQUERY] Streaming {len(rows_to_insert)} items to {TABLE_REF}...")
                    bq_client = bigquery.Client(project=PROJECT_ID)
                    errors = bq_client.insert_rows_json(TABLE_REF, rows_to_insert)
                    
                    if errors:
                        print(f"❌ [BIGQUERY] Ingestion errors: {json.dumps(errors, indent=2)}")
                    else:
                        print("🎉 [BIGQUERY] Output successfully streaming ingested into BigQuery!")
                else:
                    print("⚠️ [BIGQUERY] Aborting ingestion: No valid signal rows found.")

            except json.JSONDecodeError as decode_error:
                print(f"🚨 [PARSING ERROR] Agent output was not valid JSON:\n{clean_text}")
            except Exception as bq_err:
                print(f"❌ [BIGQUERY] Error during data preparation/ingestion: {bq_err}")

            # 4. Dispatch Email Report via Gmail SMTP
            print("📧 [ORCHESTRATOR] Dispatching email report...")
            await loop.run_in_executor(None, build_summary_email_and_send, rows_to_insert, target_date_str)

        # 5. Cleanup Session Context
        await asyncio.sleep(1) 
        print(f"\n🗑️ Deleting active session context: {SESSION_ID}")
        try:
            await make_request(client, "DELETE", current_session_endpoint)
            print("✅ Session torn down cleanly.")
        except Exception as e:
            print(f"⚠️ Warning: Session deletion failed: {e}")


if __name__ == "__main__":
    if sys.version_info < (3, 9):
        print("🚨 ERROR: Python 3.9+ required.")
        sys.exit(1)
        
    # --- Calculate PREVIOUS DAY (Yesterday) ---
    yesterday = datetime.utcnow() - timedelta(days=1)
    target_date_str = yesterday.strftime('%Y-%m-%d')
    
    QUERY = f"Execute full schema discovery and quantitative trend analysis for market snapshot date: {target_date_str}."
    
    try:
        asyncio.run(amain(QUERY, target_date_str))
    except Exception as e:
        print(f"FATAL SYSTEM FAILURE: {e}")