import pytest
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool

# Import the current agent and instruction string
from congress_trades_agent.congress_agents import (
    congress_researcher,
    RESEARCHER_INSTRUCTION,
)


def test_congress_researcher_agent_baseline():
    """Baseline test verifying the current LlmAgent setup before skills refactoring."""
    # 1. Verify agent type and metadata
    assert isinstance(congress_researcher, LlmAgent)
    assert congress_researcher.name == "CongressResearcher"
    assert congress_researcher.model == "gemini-2.5-flash"
    assert congress_researcher.output_key == "political_context"

    # 2. Verify instruction content matches declaration
    assert congress_researcher.instruction == RESEARCHER_INSTRUCTION
    assert "Washington Policy Strategist & Congress Scout" in congress_researcher.instruction
    assert "fetch_congress_signals_tool(analysis_date)" in congress_researcher.instruction

    # 3. Verify tool attachment
    assert len(congress_researcher.tools) == 1
    tool = congress_researcher.tools[0]
    assert isinstance(tool, FunctionTool)
    assert tool.func.__name__ == "fetch_congress_signals_tool"




def test_congress_researcher_agent_skill_migration():
    """Verifies that CongressResearcher is correctly loaded via the Skills Framework."""
    # 1. Verify agent metadata
    assert isinstance(congress_researcher, LlmAgent)
    assert congress_researcher.name == "CongressResearcher"
    assert congress_researcher.model == "gemini-2.5-flash"
    assert congress_researcher.output_key == "political_context"

    # 2. Verify instruction loaded from SKILL.md
    assert "Washington Policy Strategist & Congress Scout" in congress_researcher.instruction
    assert "fetch_congress_signals_tool(analysis_date)" in congress_researcher.instruction

    # 3. Verify tool attachment
    assert len(congress_researcher.tools) == 1
    tool = congress_researcher.tools[0]
    assert isinstance(tool, FunctionTool)
    assert tool.func.__name__ == "fetch_congress_signals_tool"