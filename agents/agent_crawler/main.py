import os

import uvicorn
from fastapi import FastAPI
from google.adk.cli.fast_api import get_fast_api_app

# Get the directory where main.py is located
AGENT_DIR = os.path.dirname(os.path.abspath(__file__))
# Example session service URI (e.g., SQLite)
SESSION_SERVICE_URI = "sqlite:///./sessions.db"
# Example allowed origins for CORS
ALLOWED_ORIGINS = ["http://localhost", "http://localhost:8080", "*"]
# Set web=True if you intend to serve a web interface, False otherwise
SERVE_WEB_INTERFACE = True

# Call the function to get the FastAPI app instance
# Ensure the agent directory name ('capital_agent') matches your agent folder
app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

import os
import uvicorn
import httpx # Recommended for API-based email sending
from fastapi import FastAPI, BackgroundTasks, HTTPException
from google.adk.cli.fast_api import get_fast_api_app

# ... your existing AGENT_DIR and config code ...

app: FastAPI = get_fast_api_app(
    agents_dir=AGENT_DIR,
    session_service_uri=SESSION_SERVICE_URI,
    allow_origins=ALLOWED_ORIGINS,
    web=SERVE_WEB_INTERFACE,
)

# --- NEW EMAIL LOGIC ---

async def send_email_via_api(subject: str, body: str):
    """Sends email via a third-party API (Example: SendGrid)"""
    api_key = os.environ.get("c")
    sender = 'gcp_cloud_mm@outlook.com'
    recipient = 'mmistroni@gmail.com'
    
    if not api_key:
        print("CRITICAL: No EMAIL_API_KEY found in environment variables.")
        return

    # Example for SendGrid HTTP API
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "https://api.sendgrid.com/v3/mail/send",
            headers={"Authorization": f"Bearer {api_key}"},
            json={
                "personalizations": [{"to": [{"email": recipient}]}],
                "from": {"email": sender},
                "subject": subject,
                "content": [{"type": "text/plain", "value": body}]
            }
        )
        print(f"Email status: {response.status_code}")

@app.post("/trigger-price-monitor")
async def trigger_monitor(background_tasks: BackgroundTasks):
    """
    1. Triggers the agent (you'll need to import your agent instance here)
    2. Formats the email
    3. Sends it in the background
    """
    # Note: You'll need to import your actual agent object here
    from agent_crawler.agent import root_agent
    
    try:
        # Run your agent logic
        result = await root_agent.run("Check Ray-Ban prices")
        
        # Extract the content from the LLM's response
        email_body = result.data # If using Pydantic AI result_type
        email_subject = "Price Update - Ray-Ban Meta"
        
        background_tasks.add_task(send_email_via_api, email_subject, email_body)
        
        return {"message": "Agent monitoring started, email queued."}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

# --- END EMAIL LOGIC ---

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=int(os.environ.get("PORT", 8080)))