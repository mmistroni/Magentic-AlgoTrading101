import os
import uvicorn
import httpx
import asyncio
from fastapi import FastAPI, BackgroundTasks, HTTPException
from pydantic import BaseModel
from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types
import logging
import sys
import json
import logging
from fastapi import Request, BackgroundTasks, HTTPException
from pydantic import ValidationError


# 1. Import your actual agent object
# Ensure the folder is named 'agent_crawler' and has an '__init__.py'
from tfl_agent.agent import root_agent
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s: %(message)s",
    stream=sys.stdout 
)

app = FastAPI()
app_name = "tfl_agent" # Ensure this matches your Runner's app_name
# 2. Setup the ADK Runner manually
# This is the "Engine" that will run your agent code
session_service = InMemorySessionService()
runner = Runner(
    app_name=app_name, # <--- THIS WAS MISSING
    agent=root_agent, 
    session_service=session_service
)
# 3. Define the Request Body for Cloud Scheduler
class MonitorRequest(BaseModel):
    
    query: str
    subject_line: str = "Fairlop to Bromley Journey"
    recipient: str = "mmistroni@gmail.com"



@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request, exc):
    # This prints the specific error to your Cloud Run logs
    logging.info(f"CRITICAL: Validation failed! Errors: {exc.errors()}")
    logging.info(f"CRITICAL: The body received was: {exc.body}")

    return JSONResponse(
        status_code=422,
        content={"detail": exc.errors(), "body": exc.body},
    )
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

@app.post("/trigger-route-check")
async def trigger_monitor(request: Request, background_tasks: BackgroundTasks):
    try:
        # 1. Capture the raw body as bytes and decode to string
        body_bytes = await request.body()
        body_str = body_bytes.decode("utf-8")
        
        logging.info(f"Raw body received: {body_str}")

        # 2. Parse and Validate the body
        # We try to load it as JSON first. If Cloud Scheduler sends it as a 
        # stringified JSON, this will unwrap it.
        try:
            # model_validate_json is the best tool here; it handles the 
            # string-to-object conversion and validation in one go.
            monitor_req = MonitorRequest.model_validate_json(body_str)
        except ValidationError as ve:
            logging.error(f"Validation failed. Errors: {ve.errors()}")
            # Fallback: some versions of Scheduler might send a 'proper' dict
            # if the headers finally start working.
            try:
                data = json.loads(body_str)
                monitor_req = MonitorRequest(**data)
            except Exception:
                raise HTTPException(status_code=422, detail=str(ve.errors()))

        # 3. Proceed with Agent Logic using monitor_req
        session_id = f"job_{os.urandom(4).hex()}"
        user_id = "system_scheduler"

        # --- THE FIX: Explicitly create the session in ADK ---
        await runner.session_service.create_session(
            app_name=app_name,
            user_id=user_id,
            session_id=session_id
        )
        logging.info(f"Created ADK session: {session_id}")



        
        logging.info(f"Processing query: {monitor_req.query}")
        
        content = types.Content(
            role='user', 
            parts=[types.Part.from_text(text=monitor_req.query)]
        )
        
        final_text = ""
        async for event in runner.run_async(user_id=user_id, session_id=session_id, new_message=content):
            if event.is_final_response() and event.content.parts:
                final_text = event.content.parts[0].text
        
        logging.info(f"Agent finished. Length: {len(final_text) if final_text else 0}")

        if final_text:
            background_tasks.add_task(
                send_email_via_api, 
                monitor_req.subject_line, 
                final_text,
                monitor_req.recipient
            )
        
        return {"status": "success", "session": session_id, "query": monitor_req.query}
    
    except Exception as e:
        logging.exception("Exception occurred during /trigger-price-monitor")
        raise HTTPException(status_code=500, detail=f"Internal Server Error: {str(e)}")



if __name__ == "__main__":
    # Standard Cloud Run port 8080
    port = int(os.environ.get("PORT", 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)