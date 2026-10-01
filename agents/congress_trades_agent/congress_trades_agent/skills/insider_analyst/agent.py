from pathlib import Path
from google.adk.agents import LlmAgent, SequentialAgent
from .tools import fetch_form4_signals_tool, fetch_lobbying_signals_tool
from congress_trades_agent.schemas import InsiderContextPayload

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
insider_analyst_worker = LlmAgent(
    name="InsiderAnalystWorker",
    model="gemini-2.5-flash",
    instruction=parse_skill_instructions(SKILL_DIR),
    tools=[fetch_form4_signals_tool, fetch_lobbying_signals_tool],
    output_key="insider_notes",
)

# 2. Schema formatter: No tools, enforces InsiderContextPayload
insider_analyst_formatter = LlmAgent(
    name="InsiderAnalystFormatter",
    model="gemini-2.5-flash",
    instruction=(
        "Review the gathered insider notes in context and format the response "
        "to strictly match the required InsiderContextPayload output schema."
    ),
    output_schema=InsiderContextPayload,
    output_key="insider_context",
)

# 3. Exported sequential agent
insider_analyst = SequentialAgent(
    name="InsiderAnalyst",
    sub_agents=[
        insider_analyst_worker,
        insider_analyst_formatter,
    ],
)