from google.adk.agents import LlmAgent, SequentialAgent  
from google.adk.skills import load_skill_from_dir
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
# 1. Load the skill from the directory path
bq_skill = load_skill_from_dir("skills/bq_ingestion")

BQ_INGESTION_AGENT = LlmAgent(
    name="BQIngestionAgent", 
    model="gemini-2.5-flash",
    tools=[tool_fetch_bq_candidates],
    instruction=bq_skill.instructions
)

# ---------------------------------------------------------
# AGENT 2: News Analyst
# ---------------------------------------------------------
news_skill = load_skill_from_dir("skills/news_analyst")

NEWS_ANALYST_AGENT = LlmAgent(
    name="NewsAnalystAgent",
    model="gemini-2.5-flash",
    tools=[tool_stage_news],
    instruction=news_skill.instructions
)

# ---------------------------------------------------------
# AGENT 3: Insider Analyst
# ---------------------------------------------------------
insider_skill = load_skill_from_dir("skills/insider_analyst")
INSIDER_ANALYST_AGENT = LlmAgent(
    name="InsiderAnalystAgent",
    model="gemini-2.5-flash",
    tools=[tool_stage_insiders],
    instruction=insider_skill.instructions
)

# ---------------------------------------------------------
# AGENT 4: Quant Coordinator (Final Decision)
# ---------------------------------------------------------
quant_skill = load_skill_from_dir("skills/quant_coordinator")
QUANT_COORDINATOR_AGENT = LlmAgent(
    name="LeadQuantTrader",
    model="gemini-2.5-flash",
    tools=[tool_read_full_dossier],
    instruction=quant_skill.instructions
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