from google.adk.agents import Agent
from agent_crawler.prompts import ROOT_AGENT_INSTRUCTION
from agent_crawler.tools.scraper_tools import get_bike_price_tool, get_rayban_price_tool

from google.adk.agents import LlmAgent

from google.adk.agents import Agent
from agent_crawler.prompts import ROOT_AGENT_INSTRUCTION
# Import your generic search tool
from agent_crawler.tools.search_tools import google_search_tool

crawler_agent = Agent(
    name="price_monitoring_agent",
    model="gemini-2.0-flash", 
    description="Researches product prices and generates email reports.",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[google_search_tool],
    # REMOVED: response_type=PriceDiscovery
    # This ensures the agent can call the tool as many times as it needs 
    # and then output the clean text for your email.
)

root_agent = crawler_agent