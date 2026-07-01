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
    sendgrid_key = os.environ.get("SENDGRID_API_KEY")
    if not sendgrid_key: return

    table_rows = "".join([
        f"<tr style='background-color: {'#e6f7e9' if r.get('broker') == 'Plus500' else '#f9f9f9'};'>"
        f"<td style='padding: 10px; border: 1px solid #ddd;'>{r.get('ticker')}</td>"
        f"<td style='padding: 10px; border: 1px solid #ddd;'>{r.get('broker')}</td>"
        f"<td style='padding: 10px; border: 1px solid #ddd;'>{r.get('action')}</td>"
        f"<td style='padding: 10px; border: 1px solid #ddd;'>{r.get('conviction_score')}</td>"
        f"<td style='padding: 10px; border: 1px solid #ddd;'>{r.get('reasoning')}</td></tr>"
        for r in rows_inserted
    ])
    
    html = f"<html><body><table style='border-collapse: collapse; width: 100%;'><thead><tr><th>Ticker</th><th>Broker</th><th>Action</th><th>Score</th><th>Reasoning</th></tr></thead><tbody>{table_rows}</tbody></table></body></html>"
    sg = SendGridAPIClient(sendgrid_key)
    sg.send(Mail(from_email="gcp_cloud_mm@outlook.com", to_emails="mmistroni@gmail.com", subject="StockAgent EndOfDay Shorts", html_content=html))

async def make_request(client, method, endpoint, data=None):
    url = f"{APP_URL}{endpoint}"
    headers = {"Content-Type": "application/json"}
    return await (client.post(url, headers=headers, json=data) if method == 'POST' else client.delete(url, headers=headers))

async def amain(message_to_send):
    plus500_set = fetch_plus500_universe_set()
    async with httpx.AsyncClient(timeout=600.0) as client:
        # Create Session & Run Agent (as per existing logic)
        session_endpoint = f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
        await make_request(client, "POST", session_endpoint, data={"state": {}})
        
        run_data = {"app_name": APP_NAME, "user_id": USER_ID, "session_id": SESSION_ID, "new_message": {"role": "user", "parts": [{"text": message_to_send}]}, "streaming": False}
        response = await make_request(client, "POST", "/run", data=run_data)
        agent_text = response.json()[-1]['content']['parts'][0]['text']

        # Parse & Compile
        raw_rows = json.loads(agent_text.strip("`json\n`"))
        rows_to_insert = []
        today = datetime.utcnow().strftime('%Y-%m-%d')
        now = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S.%f UTC')

        for row in (raw_rows["final_decisions"] if isinstance(raw_rows, dict) else raw_rows):
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

        # Insert BQ & Notify
        bq_client = bigquery.Client(project=PROJECT_ID)
        if not bq_client.insert_rows_json(TABLE_REF, rows_to_insert):
            await asyncio.get_running_loop().run_in_executor(None, send_summary_email, rows_to_insert)
        
        await make_request(client, "DELETE", session_endpoint)

if __name__ == "__main__":
    asyncio.run(amain(f"Run short-selling pipeline for {datetime.utcnow().strftime('%Y-%m-%d')}."))