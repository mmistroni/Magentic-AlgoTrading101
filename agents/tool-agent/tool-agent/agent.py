from google.adk.agents import Agent
from google.adk.tools import google_search
from .prompts import ROOT_AGENT_INSTRUCTION

def get_current_time() -> dict :
    """ Get the current time in the format YYYY-MM-DD HH:MM:SS """
    from datetime import datetime
    return {"current_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

   

root_agent = Agent(
    name="tool-agent",
    model="gemini-2.0-flash",
    description="Greeting agent",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[get_current_time, google_search],
)
