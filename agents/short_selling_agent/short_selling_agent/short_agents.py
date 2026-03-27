from google_adk import LLMAgent, SequentialAgent  

# Import the wrapper tools
from short_selling_agent.stage_tools import (
    tool_fetch_bq_candidates, 
    tool_get_staged_tickers, 
    tool_stage_news, 
    tool_stage_insiders, 
    tool_read_full_dossier
)

# ---------------------------------------------------------
# AGENT 1: BigQuery Ingestion
# -------------------------------------------------------
BQ_INGESTION_AGENT = LLMAgent(
    name="BQIngestionAgent", 
    model="gemini-1.5-pro",
    tools=[tool_fetch_bq_candidates],
    system_instruction=(
        "You are Step 1 in the Short Selling Pipeline. "
        "Your ONLY job is to call the `tool_fetch_bq_candidates` tool. "
        "Do NOT output the data. Just call the tool, and when it succeeds, "
        "output exactly: 'Step 1 complete. Tickers are staged.'"
    )
)

# ---------------------------------------------------------
# AGENT 2: News Analyst
# ---------------------------------------------------------
NEWS_ANALYST_AGENT = LLMAgent(
    name="NewsAnalystAgent",
    model="gemini-1.5-pro",
    # ADDED: tool_get_staged_tickers so it knows what to search for!
    tools=[tool_get_staged_tickers, tool_stage_news],
    system_instruction=(
        "You are Step 2 in the Short Selling Pipeline. "
        "1. First, call `tool_get_staged_tickers` to find out which stocks we are analyzing today. "
        "2. For EVERY ticker returned, call the `tool_stage_news` tool. "
        "3. Once you have called the news tool for all tickers, DO NOT output the news. "
        "Simply output exactly: 'Step 2 complete. News is staged.'"
    )
)

# ---------------------------------------------------------
# AGENT 3: Insider Analyst
# ---------------------------------------------------------
INSIDER_ANALYST_AGENT = LLMAgent(
    name="InsiderAnalystAgent",
    model="gemini-1.5-pro",
    # ADDED: tool_get_staged_tickers so it knows what to search for!
    tools=[tool_get_staged_tickers, tool_stage_insiders],
    system_instruction=(
        "You are Step 3 in the Short Selling Pipeline. "
        "1. First, call `tool_get_staged_tickers` to find out which stocks we are analyzing. "
        "2. For EVERY ticker returned, call the `tool_stage_insiders` tool. "
        "3. Once you have called the insider tool for all tickers, DO NOT output the data. "
        "Simply output exactly: 'Step 3 complete. Insiders are staged.'"
    )
)

# ---------------------------------------------------------
# AGENT 4: Quant Coordinator (Final Decision)
# ---------------------------------------------------------
QUANT_COORDINATOR_AGENT = LLMAgent(
    name="LeadQuantTrader",
    model="gemini-1.5-pro",
    # ADDED: This is crucial! The Quant needs a way to read the Google Doc!
    tools=[tool_read_full_dossier], 
    system_instruction=(
        "You are the final step: The Lead Quant Trader. "
        "1. Call the `tool_read_full_dossier` tool to download the massive JSON dossier. "
        "2. This dossier contains BQ Market Data, News Catalysts, and Insider Dumping Data. "
        "3. Synthesize all of this information. "
        "For EACH stock in the dossier, write a final 'Short Report'. "
        "Assign a Conviction Score (1-10) and give a final verdict: [SHORT, AVOID, or COVER]. "
        "If 'is_squeeze_risk' is True, be highly skeptical unless the news is devastating."
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