import importlib.util
from pathlib import Path
from google.adk.agents import LlmAgent
from pathlib import Path

SKILL_DIR = Path(__file__).parent

# Dynamically load tools.py using absolute file path to bypass hyphenated directory import errors
tool_path = SKILL_DIR / "tools.py"
spec = importlib.util.spec_from_file_location("bq_scout_tools_internal", tool_path)
bq_scout_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bq_scout_tools)

# Extract the wrapped tool function
fetch_clinical_signals_tool = bq_scout_tools.fetch_clinical_signals_tool


def parse_skill_instructions(skill_dir: Path) -> str:
    """Extracts instructions from SKILL.md without triggering directory validation."""
    skill_file = skill_dir / "SKILL.md"
    content = skill_file.read_text(encoding="utf-8")
    if content.startswith("---"):
        parts = content.split("---", 2)
        if len(parts) >= 3:
            return parts[2].strip()
    return content.strip()


bq_scout = LlmAgent(
    name="BQScout",
    model="gemini-2.5-flash",
    instruction=parse_skill_instructions(SKILL_DIR),
    tools=[fetch_clinical_signals_tool],
    output_key="clinical_signals",
)