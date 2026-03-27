from google_adk import LLMAgent, SequentialAgent  
from short_selling_agent.stage_tools import (
    tool_fetch_bq_candidates, 
    tool_stage_news, 
    tool_stage_insiders, 
    tool_read_full_dossier
)

# ---------------------------------------------------------
# AGENT 1: BigQuery Ingestion
# ---------------------------------------------------------
BQ_INGESTION_AGENT = LLMAgent(
    name="BQIngestionAgent", 
    model="gemini-1.5-pro",
    tools=[tool_fetch_bq_candidates], # EXACTLY ONE TOOL
    system_instruction=(
        "You are Step 1. Call your `tool_fetch_bq_candidates` tool. "
        "The tool will return a list of tickers. "
        "Your final output must be exactly: 'The tickers to analyze are: [Insert Tickers Here]'"
    )
)

# ---------------------------------------------------------
# AGENT 2: News Analyst
# ---------------------------------------------------------
NEWS_ANALYST_AGENT = LLMAgent(
    name="NewsAnalystAgent",
    model="gemini-1.5-pro",
    tools=[tool_stage_news], # EXACTLY ONE TOOL
    system_instruction=(
        "You are Step 2. You will receive a list of tickers from Step 1. "
        "For EACH ticker in that list, you must call your `tool_stage_news` tool. "
        "Wait for the tool to succeed for every ticker. "
        "Once you have fetched news for all of them, your final output must be exactly: "
        "'News is staged. The tickers to analyze are: [Insert Tickers Here]'"
    )
)

# ---------------------------------------------------------
# AGENT 3: Insider Analyst
# ---------------------------------------------------------
INSIDER_ANALYST_AGENT = LLMAgent(
    name="InsiderAnalystAgent",
    model="gemini-1.5-pro",
    tools=[tool_stage_insiders], # EXACTLY ONE TOOL
    system_instruction=(
        "You are Step 3. You will receive a list of tickers from Step 2. "
        "For EACH ticker in that list, you must call your `tool_stage_insiders` tool. "
        "Wait for the tool to succeed for every ticker. "
        "Once you have fetched insiders for all of them, your final output must be exactly: "
        "'Insiders are staged. The tickers are ready for the Quant Coordinator.'"
    )
)

# ---------------------------------------------------------
# AGENT 4: Quant Coordinator (Final Decision)
# ---------------------------------------------------------
QUANT_COORDINATOR_AGENT = LLMAgent(
    name="LeadQuantTrader",
    model="gemini-1.5-pro",
    tools=[tool_read_full_dossier], # EXACTLY ONE TOOL
    system_instruction=(
        "You are Step 4: The Lead Quant Trader. "
        "Call your `tool_read_full_dossier` tool to download the massive JSON dossier containing "
        "Market Data, News, and Form 4 Insider Sales. "
        "Synthesize all this data. For EACH stock, write a final 'Short Report'. "
        "Assign a Conviction Score (1-10) and give a final verdict: [SHORT, AVOID, or COVER]."
    )
)

# ---------------------------------------------------------
# BUILD THE PIPELINE
# ---------------------------------------------------------
SHORT_SELLING_PIPELINE = SequentialAgent(
    name="ShortSellingPipeline_V1",
    sub_agents=[
        BQ_INGESTION_AGENT,          
        NEWS_ANALYST_AGENT,          
        INSIDER_ANALYST_AGENT,       
        QUANT_COORDINATOR_AGENT      
    ]
)