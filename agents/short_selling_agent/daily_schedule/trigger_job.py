import os
import json
import subprocess
import asyncio
from typing import Dict, Any, List
from datetime import datetime
import httpx 
import sys
from google.cloud import bigquery
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
# --- SendGrid Imports ---
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, HtmlContent, Subject, To, From

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

# --- EMAIL NOTIFICATION LAYER (SENDGRID) ---

def send_strategy_report(subject: str, body_text: str):
    # Configuration
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    SENDER_EMAIL = "mmistroni@gmail.com"
    RECEIVER_EMAIL = "mmistroni@gmail.com"
    
    # Retrieve the 16-character app password securely from environment variables
    APP_PASSWORD = os.getenv("EMAIL_PASSWORD")
    
    if not APP_PASSWORD:
        raise ValueError("EMAIL_PASSWORD environment variable is not set!")

    # Build the email headers and body
    msg = MIMEMultipart()
    msg['From'] = SENDER_EMAIL
    msg['To'] = RECEIVER_EMAIL
    msg['Subject'] = subject
    msg.attach(MIMEText(body_text, 'plain'))

    # Connect and send via Gmail's native servers
    try:
        with smtplib.SMTP(SMTP_SERVER, SMTP_PORT) as server:
            server.starttls()  # Secure the connection using TLS
            server.login(SENDER_EMAIL, APP_PASSWORD)
            server.sendmail(SENDER_EMAIL, RECEIVER_EMAIL, msg.as_string())
        print("Report sent successfully via Gmail SMTP!")
    except Exception as e:
        print(f"Failed to send email: {e}")




def send_summary_email(rows_inserted: List[Dict[str, Any]]):
    """
    Synchronous worker wrapping SendGrid HTTP API calls. 
    Constructs an HTML summary matrix table or an empty-state confirmation.
    """
    print('============= SENDING SUMMARY EMAIL NOTIFICATION LAYER =============')
    sendgrid_key = os.environ.get("SENDGRID_API_KEY")
    if not sendgrid_key:
        print("⚠️ [NOTIFICATION] SENDGRID_API_KEY env parameter missing. Aborting email dispatch.")
        return

    sender_email = "gcp_cloud_mm@outlook.com"
    receiver_email = "mmistroni@gmail.com"
    today_str = datetime.utcnow().strftime('%Y-%m-%d')

    # 1. Determine Subject Line and Content Block Based on Data Presence
    if not rows_inserted:
        # Neutral, human-like log format to prevent spam filtering
        subject_str = f"Overnight MarketStats {today_str} "
        
        display_content = """
        <div style="padding: 15px; background-color: #fdfefe; border: 1px solid #e2e8f0; border-left: 4px solid #94a3b8; border-radius: 4px;">
            <p style="margin: 0; font-size: 14px; color: #334155; font-weight: bold;">
                No matching trade candidates met the strategy criteria for today's market scan.
            </p>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #64748b;">
                The execution pipeline finalized checks successfully and stood down with an empty staging state.
            </p>
        </div>
        """
    else:
        subject_str = f"Daily strategy operations report - {today_str} - processed items"
        
        table_rows = ""
        for r in rows_inserted:
            action = r.get("action", "AVOID")
            if action == "SHORT" and r.get("conviction_score", 0) >= 7:
                bg_color = "#ffe6eb"
                text_color = "#cc0033"
            elif action == "SHORT":
                bg_color = "#fff2e6"
                text_color = "#b35900"
            elif "AUTOMATED_CRITIQUE_FAILED" in str(r.get("reasoning", "")):
                bg_color = "#f2f2f2"
                text_color = "#666666"
            else:
                bg_color = "#e6f7e9"
                text_color = "#1e5a2c"

            table_rows += f"""
            <tr style="background-color: {bg_color}; color: {text_color}; font-size: 13px;">
                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{r.get('ticker')}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold;">{action}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center;">{r.get('conviction_score')}/10</td>
                <td style="padding: 10px; border: 1px solid #ddd; line-height: 1.4;">{r.get('reasoning')}</td>
            </tr>
            """
            
        display_content = f"""
        <table style="width: 100%; border-collapse: collapse; min-width: 500px;">
            <thead>
                <tr style="background-color: #2c3e50; color: white; text-align: left;">
                    <th style="padding: 12px; border: 1px solid #ddd;">Ticker</th>
                    <th style="padding: 12px; border: 1px solid #ddd; text-align: center;">Action</th>
                    <th style="padding: 12px; border: 1px solid #ddd; text-align: center;">Conviction</th>
                    <th style="padding: 12px; border: 1px solid #ddd;">Analytical Reasoning / Telemetry Flags</th>
                </tr>
            </thead>
            <tbody>
                {table_rows}
            </tbody>
        </table>
        """

    # 2. Assemble Clean, Non-Spammy HTML Document Blueprint
    html_content = f"""
    <html>
    <body style="font-family: Arial, sans-serif; color: #333333; margin: 20px;">
        <h2 style="color: #2c3e50; border-bottom: 2px solid #2c3e50; padding-bottom: 10px; font-weight: normal; font-size: 20px;">
            Multi-Agent Pipeline Execution Summary
        </h2>
        <p style="font-size: 13px; margin: 4px 0;"><strong>Execution Date:</strong> {today_str}</p>
        <p style="font-size: 13px; margin: 4px 0;"><strong>Session Context ID:</strong> <code>{SESSION_ID}</code></p>
        <br>
        {display_content}
        <br>
        <p style="font-size: 11px; color: #7f8c8d; border-top: 1px solid #eeeeee; padding-top: 10px;">
            Automated Operational Signal • Generated via Short Selling Agent Cluster Node
        </p>
    </body>
    </html>
    """

    message = Mail(
        from_email=From(sender_email, "GCP Cloud Core System"),
        to_emails=To(receiver_email),
        subject=Subject(subject_str),
        html_content=HtmlContent(html_content)
    )

    try:
        print(f"📤 [NOTIFIER] Transmitting SendGrid payload from {sender_email} to {receiver_email}...")
        sg = SendGridAPIClient(sendgrid_key)
        response = sg.send(message)
        if response.status_code in [200, 201, 202]:
            print("📨 [NOTIFIER] Summary dashboard email successfully delivered to SendGrid network gateway.")
        else:
            print(f"⚠️ [NOTIFIER] Unexpected SendGrid API response status received: {response.status_code}")
    except Exception as mail_err:
        print(f"❌ [NOTIFIER] Failed sending execution alert through SendGrid API service: {mail_err}")

    print('============= SENDING SUMMARY EMAIL VIA PYTHON =============')
    send_strategy_report(f'GCP Cloud Agent Report {today_str} | {len(rows_inserted)}', html_content)
    


# --- Authentication Function (ASYNC) ---

async def get_auth_token() -> str:
    """Retrieves an OIDC Identity Token."""
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
        print(f"ℹ️ [AUTH] Metadata Server approach skipped or failed: {e}")

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
    
    print("\n==================== 📥 RAW UNARY RESPONSE FROM SERVER ====================")
    print(response.text)
    print("===========================================================================\n")
    
    try:
        agent_response = response.json()
    except Exception as parse_err:
        print(f"❌ [PARSING] Failed parsing core wrapper JSON response dictionary payload: {parse_err}")
        raise json.JSONDecodeError("Failed to parse standard Unary JSON response structure.", response.text, 0)
    
    print(f"ℹ️ [PARSING] Root payload type returned from server is: {type(agent_response)}")
    target_payload = agent_response
    
    if isinstance(agent_response, list):
        if len(agent_response) == 0:
            print("⚠️ [PARSING] Server returned an empty list [] payload.")
            return 'Agent response structural text element was returned empty.'
        target_payload = agent_response[-1]

    if isinstance(target_payload, dict):
        final_text = target_payload.get('content', {}).get('parts', [{}])[0].get('text', '')
    else:
        print(f"⚠️ [PARSING] Unexpected structure after list unwrapping: {type(target_payload)}")
        final_text = str(target_payload)
    
    if not final_text:
        print("⚠️ [PARSING] Warning: The 'text' block was empty or missing.")
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
    
    async with httpx.AsyncClient(timeout=600.0) as client:
        
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
            loop = asyncio.get_running_loop()
            clean_text = agent_text.strip()
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
                
                if isinstance(parsed_json, dict) and "final_decisions" in parsed_json:
                    print("📂 [PARSING] Detected 'final_decisions' nesting key object. Slicing inner array data...")
                    raw_rows = parsed_json["final_decisions"]
                else:
                    raw_rows = parsed_json if isinstance(parsed_json, list) else [parsed_json]
                
                print(f"📊 [PARSING] Discovered {len(raw_rows)} individual target asset evaluation rows inside data payload.")
                
                # --- NEW SAFE BIGQUERY PLUS500 CHECK LAYER ---
                plus500_shortable_tickers = set()
                try:
                    print("🔍 [BIGQUERY] Performing defensive Plus500 eligibility validation check...")
                    bq_client = bigquery.Client(project=PROJECT_ID)
                    tickers_extracted = [str(row.get("ticker", "")).upper() for row in raw_rows if row.get("ticker")]
                    
                    if tickers_extracted:
                        # Cross reference tickers against your database shortable table
                        query = f"""
                            SELECT UPPER(ticker) as ticker 
                            FROM `datascience-projects.gcp_shareloader.plus500`
                            WHERE UPPER(ticker) IN UNNEST(@tickers) AND is_available = TRUE
                        """
                        job_config = bigquery.QueryJobConfig(
                            query_parameters=[
                                bigquery.ArrayQueryParameter("tickers", "STRING", tickers_extracted)
                            ]
                        )
                        query_job = bq_client.query(query, job_config=job_config)
                        results = query_job.result(timeout=20.0) # Defensive timeout configuration
                        plus500_shortable_tickers = {row.ticker for row in results}
                        print(f"✅ [BIGQUERY] Plus500 check succeeded. Verified count: {len(plus500_shortable_tickers)}")
                except Exception as plus500_err:
                    # If this lookup fails, we swallow the error, output logs, and default to empty (assumed not plus500)
                    print(f"⚠️ [BIGQUERY] Intermittent Plus500 query lookup failure: {plus500_err}.")
                    print("ℹ️ [FALLBACK] Continuing execution loop. Defaulting tickers to 'Not Plus500 Available'.")
                    plus500_shortable_tickers = set()
                # ----------------------------------------------

                rows_to_insert = []
                today_str = datetime.utcnow().strftime('%Y-%m-%d')
                timestamp_now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f UTC')

                print("\n==================== 🛠️ COMPILING ROWS FOR BIGQUERY ====================")
                for index, row in enumerate(raw_rows):
                    ticker_upper = str(row.get("ticker", "")).upper()
                    
                    # Determine tracking metric status flags based on validation results
                    is_plus500 = ticker_upper in plus500_shortable_tickers
                    
                    compiled_row = {
                        "evaluation_date": row.get("evaluation_date", today_str),
                        "ticker": ticker_upper,
                        "conviction_score": int(row.get("conviction_score", 3)),
                        "action": str(row.get("action", "WATCH")).upper(),
                        "reasoning": row.get("reasoning", None),
                        "inserted_at": timestamp_now
                        # You can explicitly map "is_plus500": is_plus500 here if your bigquery schema has the column!
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
                        
                        # 📬 --- TRIGGER SENDGRID NOTIFICATION UPON SUCCESS ---
                        # Run via standard loop executor since sendgrid's delivery client is synchronous
                        print("📧 [ORCHESTRATOR] Initializing mail summary delivery dispatch...")
                else:
                    print("⚠️ [BIGQUERY] Aborting ingestion phase: No rows were successfully extracted or compiled.")
                
                # 📬 ALWAYS SEND EMAIL HERE (Safe from UnboundLocalError)
                print("📧 [ORCHESTRATOR] Initializing mail summary delivery dispatch...")
                await loop.run_in_executor(None, send_summary_email, rows_to_insert)
            
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
        
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    QUERY = f"Run the short-selling pipeline for {today_str}."
    
    try:
        asyncio.run(amain(QUERY))
    except Exception as e:
        print(f"FATAL SYSTEM FAILURE EXECUTION TRACE: {e}")