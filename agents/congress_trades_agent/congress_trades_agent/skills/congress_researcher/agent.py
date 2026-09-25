from pathlib import Path
from google.adk.agents import LlmAgent, SequentialAgent
from .tools import fetch_congress_signals_tool, fetch_contract_signals_tool
from congress_trades_agent.schemas import PoliticalContextPayload

SKILL_DIR = Path(__file__).parent

def parse_skill_instructions(skill_dir: Path) -> str:
    """Extracts instructions from SKILL.md without triggering directory validation."""
    skill_file = skill_dir / "SKILL.md"
    content = skill_file.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content.strip()

# 1. Research worker: Handles tool calling
congress_researcher_worker = LlmAgent(
    name="CongressResearcherWorker",
    model="gemini-2.5-flash",
    instruction=parse_skill_instructions(SKILL_DIR),
    tools=[fetch_congress_signals_tool, fetch_contract_signals_tool],
    output_key="research_notes",
)

# 2. Schema formatter: No tools, enforces PoliticalContextPayload
congress_researcher_formatter = LlmAgent(
    name="CongressResearcherFormatter",
    model="gemini-2.5-flash",
    instruction=(
        "Review the gathered research notes in context and format the response "
        "to strictly match the required output schema."
    ),
    output_schema=PoliticalContextPayload,
    output_key="political_context",
)

# 3. Exported sequential agent
congress_researcher = SequentialAgent(
    name="CongressResearcher",
    sub_agents=[
        congress_researcher_worker,
        congress_researcher_formatter,
    ],
)