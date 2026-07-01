import os
import json
import asyncio
import sys
from datetime import datetime
from google.cloud import bigquery
import httpx 

# --- SendGrid Imports ---
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail, HtmlContent, Subject, To, From

# --- Configuration ---
APP_URL = os.environ.get("AGENT_SERVICE_URL", "https://short-selling-agent-service-682143946483.us-central1.run.app")
USER_ID = "automated_cron_job"
SESSION_ID = f"session_{datetime.utcnow().strftime('%Y%m%d%H%M%S')}" 
APP_NAME = "short_selling_agent"
PROJECT_ID = "datascience-projects"
DATASET_ID = "finviz_blacklist"
TABLE_ID = "daily_recommendations"
TABLE_REF = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
PLUS500_TABLE_REF = f"{PROJECT_ID}.gcp_shareloader.plus500"

def fetch_plus500_universe_set():
    """Fetches distinct Plus500 tickers for in-memory join."""
    print("🔍 [LOOKUP] Fetching Plus500 universe from BigQuery...")
    client = bigquery.Client(project=PROJECT_ID)
    sql = f"SELECT DISTINCT UPPER(TRIM(ticker)) FROM `{PLUS500_TABLE_REF}` WHERE ticker IS NOT NULL"
    try:
        query_job = client.query(sql)
        return {row[0] for row in query_job.result()}
    except Exception as e:
        print(f"⚠️ [LOOKUP] Failed to fetch Plus500 list: {e}")
        return set()

def send_summary_email(rows_inserted):
    """Dispatches a summary table of successfully flagged short candidates."""
    sendgrid_key = os.environ.get("SENDGRID_API_KEY")
    if not sendgrid_key: 
        print("⚠️ [EMAIL] SendGrid API Key missing. Skipping notification.")
        return

    table_rows = "".join([
        f"<tr style='background-color: {'#e6f7e9' if r.get('broker') == 'Plus500' else '#f9f9f9'};'>"
        f"<td style='padding: 10px; border: 1px solid #ddd;'>{r.get('ticker')}</td>"
        f"<td style='padding: 10px; border: 1px solid #ddd;'>{r.get('broker')}</td>"
        f"<td style='padding: 10px; border: 1px solid #ddd;'>{r.get('action')}</td>"
        f"<td style='padding: 10px; border: 1px solid #ddd;'>{r.get('conviction_score')}</td>"
        f"<td style='padding: 10px; border: 1px solid #ddd;'>{r.get('reasoning')}</td></tr>"
        for r in rows_inserted
    ])
    
    html = f"<html><body><h3>Short Selling Daily Report</h3><table style='border-collapse: collapse; width: 100%;'><thead><tr style='background-color: #f2f2f2;'><th style='padding: 10px; text-align: left;'>Ticker</th><th style='padding: 10px; text-align: left;'>Broker</th><th style='padding: 10px; text-align: left;'>Action</th><th style='padding: 10px; text-align: left;'>Score</th><th style='padding: 10px; text-align: left;'>Reasoning</th></tr></thead><tbody>{table_rows}</tbody></table></body></html>"
    try:
        sg = SendGridAPIClient(sendgrid_key)
        sg.send(Mail(
            from_email="gcp_cloud_mm@outlook.com", 
            to_emails="mmistroni@gmail.com", 
            subject="StockAgent EndOfDay Shorts", 
            html_content=html
        ))
        print("✉️ [EMAIL] Summary report sent successfully.")
    except Exception as e:
        print(f"⚠️ [EMAIL] Failed to dispatch email via SendGrid: {e}")

async def make_request(client, method, endpoint, data=None):
    """Helper method for routing orchestration calls to the agent service layer."""
    url = f"{APP_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    if method == 'POST':
        return await client.post(url, headers=headers, json=data)
    elif method == 'DELETE':
        return await client.delete(url, headers=headers)

async def amain(message_to_send):
    plus500_set = fetch_plus500_universe_set()
    
    async with httpx.AsyncClient(timeout=600.0) as client:
        session_endpoint = f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
        
        # 1. Open the remote Agent Session
        print(f"🚀 Establishing orchestration session: {SESSION_ID}")
        await make_request(client, "POST", session_endpoint, data={"state": {}})
        
        try:
            # 2. Fire the execution pipeline command
            run_data = {
                "app_name": APP_NAME, 
                "user_id": USER_ID, 
                "session_id": SESSION_ID, 
                "new_message": {"role": "user", "parts": [{"text": message_to_send}]}, 
                "streaming": False
            }
            print(f"📡 Executing pipeline request: '{message_to_send}'")
            response = await make_request(client, "POST", "/run", data=run_data)
            response.raise_for_status()
            
            agent_text = response.json()[-1]['content']['parts'][0]['text']

            # 3. Parse output markdown blocks cleanly if wrapped
            clean_json_text = agent_text.strip()
            if clean_json_text.startswith("```json"):
                clean_json_text = clean_json_text[7:]
            if clean_json_text.endswith("```"):
                clean_json_text = clean_json_text[:-3]
            clean_json_text = clean_json_text.strip()

            raw_rows = json.loads(clean_json_text)
            rows_to_insert = []
            today = datetime.utcnow().strftime('%Y-%m-%d')
            now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f UTC')

            # Extract final decisions based on the returned layout structure
            decisions = []
            if isinstance(raw_rows, dict):
                decisions = raw_rows.get("final_decisions", [])
                status_msg = raw_rows.get("status", "Processed")
                print(f"📊 Agent returned payload status: '{status_msg}' with {len(decisions)} candidates.")
            elif isinstance(raw_rows, list):
                decisions = raw_rows

            for row in decisions:
                ticker = str(row.get("ticker", "")).upper()
                rows_to_insert.append({
                    "evaluation_date": row.get("evaluation_date", today),
                    "ticker": ticker,
                    "conviction_score": int(row.get("conviction_score", 3)),
                    "action": str(row.get("action", "WATCH")).upper(),
                    "reasoning": row.get("reasoning", None),
                    "inserted_at": now,
                    "broker": "Plus500" if ticker in plus500_set else "Other"
                })

            # 4. Mitigation Guardrail: Only touch BigQuery if arrays contain values
            if rows_to_insert:
                print(f"💾 Committing {len(rows_to_insert)} items to BigQuery table: {TABLE_REF}")
                bq_client = bigquery.Client(project=PROJECT_ID)
                errors = bq_client.insert_rows_json(TABLE_REF, rows_to_insert)
                
                if not errors:
                    print("✅ BigQuery sync completed safely.")
                    await asyncio.get_running_loop().run_in_executor(None, send_summary_email, rows_to_insert)
                else:
                    print(f"❌ Error inserting rows into BigQuery: {errors}")
            else:
                print("ℹ️ No eligible candidate rows generated for insertion today. Skipping BigQuery connection block safely.")

        except Exception as err:
            print(f"🚨 Pipeline tracking failed unexpectedly: {err}")
            
        finally:
            # 5. Guaranteed Cleanup Loop: Closes the remote context even if execution crashes midway
            print(f"🛑 Cleaning up and closing session context: {SESSION_ID}")
            try:
                await make_request(client, "DELETE", session_endpoint)
                print("🏁 Session cleanup verified successfully.")
            except Exception as e:
                print(f"⚠️ Warning: Session clean-up hook was unreachable: {e}")

if __name__ == "__main__":
    current_date_str = datetime.utcnow().strftime('%Y-%m-%d')
    asyncio.run(amain(f"Run short-selling pipeline for {current_date_str}."))