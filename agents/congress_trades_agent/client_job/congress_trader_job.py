import asyncio
from datetime import datetime, timedelta, timezone
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import json
import os
import re
import smtplib
import sys
from typing import Any, Dict, List

import httpx

# --- Configuration (Congress Trades Agent) ---
APP_URL = os.environ.get(
    "AGENT_SERVICE_URL",
    "https://congress-trades-agent-682143946483.us-central1.run.app",
)
USER_ID = "automated_cron_job"
SESSION_ID = f"session_{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
APP_NAME = "congress_trades_agent"

SUBJECT_PREFIX = os.environ.get("EMAIL_SUBJECT_PREFIX", "[CONGRESS_TRADES_AGENT]")


def _format_subject(target_date_str: str, status: str, count: int = 0) -> str:
  if status == "SIGNALS":
    return f"{SUBJECT_PREFIX} | {target_date_str} | {count} SIGNALS"
  return f"{SUBJECT_PREFIX} | {target_date_str} | {status}"


# --- EMAIL NOTIFICATION LAYER (GMAIL SMTP) ---


def send_strategy_report(subject: str, html_body: str, json_payload: str) -> None:
  """Synchronous worker that dispatches an HTML + JSON report via Gmail SMTP."""
  smtp_server = "smtp.gmail.com"
  smtp_port = 587
  primary_email = os.environ.get("REPORT_EMAIL", "mmistroni@gmail.com")
  app_password = (
      os.getenv("EMAIL_PASSWORD", "").replace(" ", "")
      if os.getenv("EMAIL_PASSWORD")
      else ""
  )

  if not app_password:
    print(
        "⚠️ [EMAIL] EMAIL_PASSWORD environment variable is not set! Skipping"
        " email dispatch."
    )
    return

  msg = MIMEMultipart("alternative")
  msg["From"] = primary_email
  msg["To"] = primary_email
  msg["Subject"] = subject

  plain_text = (
      f"Subject: {subject}\n"
      f"Analysis Date: {subject}\n\n"
      f"JSON Result:\n{json_payload}\n"
  )
  msg.attach(MIMEText(plain_text, "plain"))
  msg.attach(MIMEText(html_body, "html"))

  try:
    print(f"📤 [EMAIL] Transmitting report to {primary_email} via Gmail SMTP...")
    with smtplib.SMTP(smtp_server, SMTP_PORT) as server:
      server.starttls()
      server.login(primary_email, app_password)
      server.sendmail(primary_email, primary_email, msg.as_string())
    print("📨 [EMAIL] Report sent successfully via Gmail SMTP!")
  except Exception as e:
    print(f"❌ [EMAIL] Failed to send email via SMTP to {primary_email}: {e}")


def _extract_json_payload(raw_text: str, target_date_str: str) -> Dict[str, Any]:
  """Extracts structured JSON from agent text, or wraps raw output cleanly as JSON."""
  text = raw_text.strip()

  # Strip ```json ... ``` or ``` ... ``` fences if present
  fenced_match = re.search(r"```(?:json)?\s*([\s\S]*?)\s*```", text, re.IGNORECASE)
  candidate = fenced_match.group(1).strip() if fenced_match else text

  try:
    parsed = json.loads(candidate)
    if isinstance(parsed, dict):
      parsed.setdefault("analysis_date", target_date_str)
      parsed.setdefault("session_id", SESSION_ID)
      return parsed
    return {
        "analysis_date": target_date_str,
        "session_id": SESSION_ID,
        "items": parsed,
    }
  except json.JSONDecodeError:
    return {
        "analysis_date": target_date_str,
        "session_id": SESSION_ID,
        "status": "RAW_OUTPUT",
        "raw_response": raw_text,
    }


def _extract_rows_for_display(result_obj: Dict[str, Any]) -> List[Dict[str, Any]]:
  for key in ("signals", "decisions", "candidates", "items"):
    val = result_obj.get(key)
    if isinstance(val, list) and val and isinstance(val[0], dict):
      return val
  return []


def build_summary_email_and_send(
    result_obj: Dict[str, Any], target_date_str: str, is_error: bool = False
) -> None:
  """Constructs a responsive HTML + JSON email and triggers Gmail SMTP dispatch."""
  print("============= GENERATING OPERATIONAL SUMMARY EMAIL =============")
  pretty_json = json.dumps(result_obj, indent=2, default=str)
  rows = _extract_rows_for_display(result_obj)

  if is_error:
    subject_str = _format_subject(target_date_str, "ERROR")
    display_content = """
        <div style="padding: 15px; background-color: #fff5f5; border: 1px solid #feb2b2; border-left: 4px solid #c53030; border-radius: 4px;">
            <p style="margin: 0; font-size: 14px; color: #742a2a; font-weight: bold;">
                Pipeline execution encountered an error. Inspect the JSON payload below.
            </p>
        </div>
        """
  elif not rows:
    subject_str = _format_subject(target_date_str, "EMPTY")
    display_content = """
        <div style="padding: 15px; background-color: #fdfefe; border: 1px solid #e2e8f0; border-left: 4px solid #94a3b8; border-radius: 4px;">
            <p style="margin: 0; font-size: 14px; color: #334155; font-weight: bold;">
                No structured signal items were returned for this analysis date.
            </p>
            <p style="margin: 4px 0 0 0; font-size: 13px; color: #64748b;">
                See the JSON payload below for full details.
            </p>
        </div>
        """
  else:
    subject_str = _format_subject(target_date_str, "SIGNALS", count=len(rows))
    table_rows = ""
    for r in rows:
      action = str(r.get("action", r.get("signal", "HOLD"))).upper()
      if action in ("BUY", "LONG", "STRONG_BUY"):
        bg_color, text_color = "#e6f7e9", "#1e5a2c"
      elif action in ("SELL", "SHORT", "STRONG_SELL"):
        bg_color, text_color = "#ffe6eb", "#cc0033"
      else:
        bg_color, text_color = "#f8f9fa", "#495057"

      score = r.get("conviction_score", r.get("confidence_score", "N/A"))
      reasoning = r.get("reasoning", r.get("rationale", "N/A"))

      table_rows += f"""
            <tr style="background-color: {bg_color}; color: {text_color}; font-size: 13px;">
                <td style="padding: 10px; border: 1px solid #ddd; font-weight: bold;">{r.get('ticker', 'N/A')}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold;">{action}</td>
                <td style="padding: 10px; border: 1px solid #ddd; text-align: center; font-weight: bold;">{score}</td>
                <td style="padding: 10px; border: 1px solid #ddd; line-height: 1.4;">{reasoning}</td>
            </tr>
            """

    display_content = f"""
        <table style="width: 100%; border-collapse: collapse; min-width: 500px;">
            <thead>
                <tr style="background-color: #1a365d; color: white; text-align: left;">
                    <th style="padding: 12px; border: 1px solid #ddd;">Ticker</th>
                    <th style="padding: 12px; border: 1px solid #ddd; text-align: center;">Action</th>
                    <th style="padding: 12px; border: 1px solid #ddd; text-align: center;">Score</th>
                    <th style="padding: 12px; border: 1px solid #ddd;">Summary</th>
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
            Congress Trades Agent Execution Report
        </h2>
        <p style="font-size: 13px; margin: 4px 0;"><strong>Analysis Date:</strong> {target_date_str}</p>
        <p style="font-size: 13px; margin: 4px 0;"><strong>Session ID:</strong> <code>{SESSION_ID}</code></p>
        <br>
        {display_content}
        <h3>JSON Result</h3>
        <pre style="background-color: #f4f6f8; padding: 14px; border-radius: 6px; border: 1px solid #d0d7de; font-size: 12px; overflow-x: auto;">{pretty_json}</pre>
        <p style="font-size: 11px; color: #7f8c8d; border-top: 1px solid #eeeeee; padding-top: 10px;">
            Automated Quantitative Signal • Congress Trades Agent Cloud Run Job
        </p>
    </body>
    </html>
    """

  send_strategy_report(subject_str, html_content, pretty_json)


# --- AUTHENTICATION LAYER (ASYNC) ---


async def get_auth_token() -> str:
  """Retrieves an OIDC Identity Token for authenticating against Cloud Run."""
  print("🔑 [AUTH] Attempting to acquire OIDC token...")
  try:
    async with httpx.AsyncClient() as client:
      metadata_url = (
          "http://metadata.google.internal/computeMetadata/v1/instance/"
          "service-accounts/default/identity"
      )
      headers = {"Metadata-Flavor": "Google"}
      params = {"audience": APP_URL}

      response = await client.get(
          metadata_url, headers=headers, params=params, timeout=5.0
      )
      if response.status_code == 200:
        print("✅ [AUTH] Token successfully acquired via GCP Metadata Server.")
        return response.text.strip()
  except Exception as e:
    print(f"ℹ️ [AUTH] Metadata Server approach skipped: {e}")

  try:
    print("ℹ️ [AUTH] Falling back to local gcloud CLI token extraction...")
    proc = await asyncio.create_subprocess_exec(
        "gcloud",
        "auth",
        "print-identity-token",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
    )
    stdout, stderr = await proc.communicate()

    if proc.returncode != 0:
      raise RuntimeError(f"gcloud command failed: {stderr.decode().strip()}")

    print("✅ [AUTH] Token successfully acquired via gcloud CLI fallback.")
    return stdout.decode().strip()
  except FileNotFoundError:
    raise RuntimeError(
        "gcloud command not found. Please ensure Google Cloud CLI is installed."
    )


# --- API INTERACTION LAYER (ASYNC) ---


async def make_request(
    client: httpx.AsyncClient,
    method: str,
    endpoint: str,
    data: Dict[str, Any] | None = None,
) -> httpx.Response:
  """Helper function for authenticated asynchronous requests using httpx."""
  token = await get_auth_token()
  headers = {
      "Authorization": f"Bearer {token}",
      "Content-Type": "application/json",
  }
  url = f"{APP_URL}{endpoint}"
  print(f"📡 [NETWORK] Dispatching {method.upper()} request to: {url}")

  try:
    if method.upper() == "POST":
      response = await client.post(url, headers=headers, json=data)
    elif method.upper() == "DELETE":
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


async def run_agent_request(
    client: httpx.AsyncClient, session_id: str, message: str
) -> str:
  """Executes a single POST request to the unary /run endpoint."""
  print(f"\n[User] -> Sending request to Unary Endpoint: '{message}'")

  run_data = {
      "app_name": APP_NAME,
      "user_id": USER_ID,
      "session_id": session_id,
      "new_message": {"role": "user", "parts": [{"text": message}]},
      "streaming": False,
  }

  response = await make_request(client, "POST", "/run", data=run_data)
  agent_response = response.json()

  target_payload = agent_response
  if isinstance(agent_response, list):
    if not agent_response:
      return ""
    target_payload = agent_response[-1]

  if isinstance(target_payload, dict):
    parts = target_payload.get("content", {}).get("parts", [])
    final_text = "".join(
        part.get("text", "")
        for part in parts
        if isinstance(part, dict) and part.get("text")
    )
  else:
    final_text = str(target_payload)

  print("\n==================== EXTRACTED AGENT OUTPUT ====================")
  print(final_text)
  print("================================================================\n")
  return final_text


# --- MAIN PIPELINE EXECUTION ---


async def amain(message_to_send: str, target_date_str: str) -> Dict[str, Any]:
  """Runs the agent for target_date_str, returns JSON result, and emails report."""
  print(
      "\n🤖 Starting Congress Trades Job | Session:"
      f" **{SESSION_ID}** | Analysis Date: **{target_date_str}**"
  )

  session_data = {
      "state": {
          "candidates": [],
          "confluence_reports": {},
          "congressional_context": {},
          "insider_context": {},
      }
  }
  current_session_endpoint = (
      f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{SESSION_ID}"
  )

  loop = asyncio.get_running_loop()

  async with httpx.AsyncClient(timeout=600.0) as client:
    try:
      await make_request(
          client, "POST", current_session_endpoint, data=session_data
      )
      agent_text = await run_agent_request(client, SESSION_ID, message_to_send)
      result_obj = _extract_json_payload(agent_text, target_date_str)

      print("==================== STRUCTURED JSON RESULT ====================")
      print(json.dumps(result_obj, indent=2, default=str))
      print("================================================================\n")

      await loop.run_in_executor(
          None, build_summary_email_and_send, result_obj, target_date_str, False
      )
      return result_obj
    except Exception as e:
      error_obj = {
          "analysis_date": target_date_str,
          "session_id": SESSION_ID,
          "status": "ERROR",
          "error": str(e),
      }
      print(f"❌ Pipeline execution error: {e}")
      await loop.run_in_executor(
          None, build_summary_email_and_send, error_obj, target_date_str, True
      )
      return error_obj
    finally:
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

  if len(sys.argv) > 1:
    target_date_str = sys.argv[1]
  else:
    yesterday = datetime.now(timezone.utc) - timedelta(days=1)
    target_date_str = yesterday.strftime("%Y-%m-%d")

  query = (
      "Run the full congressional and insider trade analysis pipeline for "
      f"analysis_date {target_date_str}. Discover active candidate tickers from "
      "the signals and synthesize the trade evaluation. Return the final "
      "summary as valid JSON."
  )

  final_result = asyncio.run(amain(query, target_date_str))
  print(json.dumps(final_result, default=str))