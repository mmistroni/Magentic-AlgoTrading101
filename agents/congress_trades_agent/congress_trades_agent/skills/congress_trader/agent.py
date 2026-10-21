from pathlib import Path
from google.adk.agents import LlmAgent, SequentialAgent
from .tools import (
    fetch_fmp_fundamentals,
    store_trade_decision,
    fetch_historical_episodes
)

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

# Research & Execution worker equipped with fundamental tools and BQ episodic memory
congress_trader = LlmAgent(
    name="CongressTrader",
    model="gemini-3.5-flash",
    instruction=parse_skill_instructions(SKILL_DIR),
    tools=[
        fetch_fmp_fundamentals,
        store_trade_decision,
        fetch_historical_episodes
    ],
)