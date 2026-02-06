from agent_crawler.prompts import ROOT_AGENT_INSTRUCTION, RESEARCHER_INSTRUCTION
from google.adk.agents import Agent
from google.adk.tools import google_search, FunctionTool
from google.adk.tools.agent_tool import AgentTool # The "wrapper" for specialists
from agent_crawler.tools.scraper_tools import track_and_log_price# Custom function for price history logic


# 1. THE SPECIALIST (Built-in Tool goes here)
# This agent has only ONE job: Search.
search_specialist = Agent(
    name="search_expert",
    model="gemini-2.0-flash",
    description="A specialist that finds current retail prices using Google Search.",
    instruction=RESEARCHER_INSTRUCTION,
    tools=[google_search] # The 1 allowed built-in tool
)


# 3. THE ROOT AGENT (The Orchestrator)
# This agent coordinates the specialist and the custom functions.
root_agent = Agent(
    name="price_monitoring_agent",
    model="gemini-2.0-flash",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[
        AgentTool(search_specialist), # We wrap the specialist so it looks like a tool
        FunctionTool(track_and_log_price) # Custom logic
    ]
)