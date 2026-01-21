from google.adk.agents import Agent
from agent_crawler.prompts import ROOT_AGENT_INSTRUCTION
from agent_crawler.tools.scrapers import get_rayban_price_tool, get_bike_price_tool
from google.adk.agents import LlmAgent

crawler_agent = Agent(
    name="price_monitoring_agent",
    model="gemini-2.0-flash", 
    description="Analyzes bike and eyewear prices for automated email reports.",
    instruction=PROMPT_INSTRUCTIONS,  # Changed to match your variable
    tools=[
        get_bike_price_tool,          # Added your scraping tools
        get_rayban_price_tool
    ],
)
root_agent = crawler_agent