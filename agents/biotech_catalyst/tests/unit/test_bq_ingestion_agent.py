import pytest
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Import the current agent and instruction string
from biotech_catalyst.catalyst_agents import (
    bq_scout_agent,
    BQ_SKILL_PATH
)


def test_bq_scout_agent_baseline():
    """Baseline test verifying the current LlmAgent setup and skill directory existence."""
    # 1. Verify agent type, name, and model
    assert isinstance(bq_scout_agent, LlmAgent)
    assert bq_scout_agent.name == "BQScoutAgent"
    assert bq_scout_agent.model == "gemini-2.5-flash"

    # 2. Verify the skill directory and SKILL.md file exist on disk
    assert BQ_SKILL_PATH.exists()
    assert (BQ_SKILL_PATH / "SKILL.md").exists()