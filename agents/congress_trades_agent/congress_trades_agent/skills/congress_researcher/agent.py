from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.skills import load_skill_from_dir
from .tools import fetch_congress_signals_tool

SKILL_DIR = Path(__file__).parent
researcher_skill = load_skill_from_dir(SKILL_DIR)

congress_researcher = LlmAgent(
    name="CongressResearcher",
    model='gemini-2.5-flash',
    instruction=researcher_skill.instructions,
    tools=[fetch_congress_signals_tool],
    output_key="political_context"
)