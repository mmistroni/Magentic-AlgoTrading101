from google.adk.agents import LlmAgent, SequentialAgent  
from short_selling_agent.prompts import BQ_ANALYST_INSTRUCTIONS,\
                    NEWS_ANALYST_INSTRUCTIONS, INSIDER_ANALYST_INSTRUCTIONS, QUANT_COORDINATOR_INSTRUCTIONS
from short_selling_agent.stage_tools import (
    tool_fetch_bq_candidates, 
    tool_stage_news, 
    tool_stage_insiders, 
    tool_read_full_dossier
)

# ---------------------------------------------------------
# AGENT 1: BigQuery Ingestion
# ---------------------------------------------------------
BQ_INGESTION_AGENT = LlmAgent(
    name="BQIngestionAgent", 
    model="gemini-2.5-flash",
    tools=[tool_fetch_bq_candidates],
    instruction=BQ_ANALYST_INSTRUCTIONS
)

# ---------------------------------------------------------
# AGENT 2: News Analyst
# ---------------------------------------------------------
NEWS_ANALYST_AGENT = LlmAgent(
    name="NewsAnalystAgent",
    model="gemini-2.5-flash",
    tools=[tool_stage_news],
    instruction=NEWS_ANALYST_INSTRUCTIONS
)

# ---------------------------------------------------------
# AGENT 3: Insider Analyst
# ---------------------------------------------------------
INSIDER_ANALYST_AGENT = LlmAgent(
    name="InsiderAnalystAgent",
    model="gemini-2.5-flash",
    tools=[tool_stage_insiders],
    instruction=INSIDER_ANALYST_INSTRUCTIONS
)

# ---------------------------------------------------------
# AGENT 4: Quant Coordinator (Final Decision)
# ---------------------------------------------------------
QUANT_COORDINATOR_AGENT = LlmAgent(
    name="LeadQuantTrader",
    model="gemini-2.5-flash",
    tools=[tool_read_full_dossier],
    instruction=QUANT_COORDINATOR_INSTRUCTIONS
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