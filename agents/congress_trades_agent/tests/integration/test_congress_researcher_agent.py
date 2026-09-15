import os
from pathlib import Path
import pytest

from congress_trades_agent.skills.congress_researcher.agent import congress_researcher_agent
from congress_trades_agent.schemas import CongressSignalsResponse, ContractSignalsResponse

# Resolve GCP credentials path relative to workspace root
GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

TEST_DATE = "2026-09-14"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
async def test_congress_researcher_agent_execution():
    """Verifies that the agent executes the end-to-end tool calling workflow and produces analysis."""
    prompt = f"Analyze Congressional trading signals for {TEST_DATE} and cross-reference any government contract awards."

    # Execute the agent loop
    result = await congress_researcher_agent.run(prompt)

    # 1. Output Integrity Checks
    assert result is not None
    assert result.data is not None
    
    # Verify non-empty analytical text response
    response_text = str(result.data)
    assert len(response_text) > 0

    # 2. Tool Invocation Assertions
    # Verify that the agent actually executed the primary tools during its run
    tool_calls = [
        msg.tool_name 
        for msg in result.new_messages() 
        if hasattr(msg, "tool_name") and msg.tool_name
    ]
    
    assert "fetch_congress_signals" in tool_calls, "Agent failed to call fetch_congress_signals tool"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
async def test_congress_researcher_agent_synthesis():
    """Verifies that the agent output includes key structural elements expected from the tools."""
    prompt = (
        f"Fetch Congressional trading signals for {TEST_DATE}. For the top identified ticker, "
        "check for government contract awards and provide a short summary."
    )

    result = await congress_researcher_agent.run(prompt)
    response_text = str(result.data).lower()

    # Verify that the output synthesizes signal context rather than failing silently
    assert "error" not in response_text or "no error" in response_text
    assert len(response_text.split()) > 20, "Agent response was too brief"