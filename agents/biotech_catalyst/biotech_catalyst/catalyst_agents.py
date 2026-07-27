from google.adk.agents import LlmAgent, SequentialAgent  
from google.adk.skills import load_skill_from_dir
from pathlib import Path

# ---------------------------------------------------------
# AGENT 1: BigQuery Ingestion
# ---------------------------------------------------------
# 1. Load the skill from the directory path

CURRENT_DIR = Path(__file__).parent
BQ_SKILL_PATH = CURRENT_DIR / "skills" / "bq-scout"

bq_skill = load_skill_from_dir(str(BQ_SKILL_PATH))

bq_scout_agent = LlmAgent(
    name="BQScoutAgent", 
    model="gemini-2.5-flash",
    output_key="clinical_signals",  # <-- Add this parameter here
)
# ----------------------------------------------------