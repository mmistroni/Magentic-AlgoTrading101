import os
import uvicorn
import httpx
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

# 1. Import your actual agent object
# Ensure the folder is named 'agent_crawler' and has an '__init__.py'
from agent_crawler.agent import root_agent

app = FastAPI()

# 2. Setup the ADK Runner manually
# This is the "Engine" that will run your agent code
session_service = InMemorySessionService()
runner = Runner(
    app_name="crawler_agent", # <--- THIS WAS MISSING
    agent=root_agent, 
    session_service=session_service
)
# 3. Define the Request Body for Cloud Scheduler
class MonitorRequest(BaseModel):
    query: str
    subject_line: str = "Price Update"
    recipient: str = "mmistroni@gmail.com"

async def send_email_via_api(subject: str, body: str, recipient: str):
    """Sends email via SendGrid HTTP API"""
    api_key = os.environ.get("EMAIL_API_KEY")
    if not api_key:
        print("CRITICAL: No EMAIL_API_KEY found.")
        return

    async with httpx.AsyncClient() as client:
        try:
            response = await client.post(
                "https://api.sendgrid.com/v3/mail/send",
                headers={"Authorization": f"Bearer {api_key}"},
                json={
                    "personalizations": [{"to": [{"email": recipient}]}],
                    "from": {"email": "gcp_cloud_mm@outlook.com"},
                    "subject": subject,
                    "content": [{"type": "text/plain", "value": body}]
                }
            )
            print(f"Email sent! Status: {response.status_code}")
        except Exception as e:
            print(f"Failed to send email: {e}")

@app.post("/trigger-price-monitor")
async def trigger_monitor(request: MonitorRequest, background_tasks: BackgroundTasks):
    try:
        # Create a unique session for this specific run
        session_id = f"job_{os.urandom(4).hex()}"
        user_id = "system_scheduler"
        
        # Format the message for the ADK Runner
        content = types.Content(role='user', parts=[types.Part.from_text(text=request.query)])
        
        final_text = ""
        # 4. Execute the agent turn
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            # Check for the final response event to get the email body
            if event.is_final_response() and event.content.parts:
                final_text = event.content.parts[0].text
        
        if final_text:
            # 5. Queue the email as a background task
            background_tasks.add_task(
                send_email_via_api, 
                request.subject_line, 
                final_text,
                request.recipient
            )
        
        return {"status": "success", "session": session_id, "query": request.query}
    
    except Exception as e:
        print(f"Error during agent execution: {e}")
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    # Standard Cloud Run port 8080
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)