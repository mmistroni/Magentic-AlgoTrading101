from pathlib import Path
from google.adk.agents import LlmAgent
from .tools import fetch_congress_signals_tool

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

congress_researcher = LlmAgent(
    name="CongressResearcher",
    model='gemini-2.5-flash',
    instruction=parse_skill_instructions(SKILL_DIR),
    tools=[fetch_congress_signals_tool],
    output_key="political_context"
)