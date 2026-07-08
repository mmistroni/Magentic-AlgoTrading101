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
from pathlib import Path

# ---------------------------------------------------------
# AGENT 1: BigQuery Ingestion
# ---------------------------------------------------------
# 1. Load the skill from the directory path

CURRENT_DIR = Path(__file__).parent
BQ_SKILL_PATH = CURRENT_DIR / "skills" / "bq_ingestion"

bq_skill = load_skill_from_dir(str(BQ_SKILL_PATH))

BQ_INGESTION_AGENT = LlmAgent(
    name="BQIngestionAgent", 
    model="gemini-2.5-flash",
    tools=[tool_fetch_bq_candidates],
    instruction=bq_skill.instructions
)

# ---------------------------------------------------------
# AGENT 2: News Analyst
# ---------------------------------------------------------

NEWS_SKILL_PATH = CURRENT_DIR / "skills" / "news_analyst"
news_skill = load_skill_from_dir(str(NEWS_SKILL_PATH))

NEWS_ANALYST_AGENT = LlmAgent(
    name="NewsAnalystAgent",
    model="gemini-2.5-flash",
    tools=[tool_stage_news],
    instruction=news_skill.instructions
)

# ---------------------------------------------------------
# AGENT 3: Insider Analyst
# ---------------------------------------------------------

INSIDER_SKILL_PATH = CURRENT_DIR / "skills" / "insider_analyst"
insider_skill = load_skill_from_dir(str(INSIDER_SKILL_PATH))
INSIDER_ANALYST_AGENT = LlmAgent(
    name="InsiderAnalystAgent",
    model="gemini-2.5-flash",
    tools=[tool_stage_insiders],
    instruction=insider_skill.instructions
)

# ---------------------------------------------------------
# AGENT 4: Quant Coordinator (Final Decision)
# ---------------------------------------------------------
QUANT_SKILL_PATH = CURRENT_DIR / "skills" / "quant_coordinator"
quant_skill = load_skill_from_dir(str(QUANT_SKILL_PATH))

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