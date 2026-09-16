import os
from pathlib import Path
import pytest

from google.adk.runners import InMemoryRunner
from google.genai import types

from congress_trades_agent.skills.congress_researcher.agent import congress_researcher

# Resolve GCP credentials path relative to workspace root
GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

TEST_DATE = "2026-09-14"
APP_NAME = "congress_trades_agent"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
async def test_congress_researcher_agent_execution():
    """Verifies that the ADK agent executes tool calls and produces an analysis response."""
    runner = InMemoryRunner(agent=congress_researcher, app_name=APP_NAME)

    user_id = "test_user"
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )

    # Formulate prompt as an ADK Content object
    prompt_text = f"Analyze Congressional trading signals for {TEST_DATE} and cross-reference any government contract awards."
    user_msg = types.Content(
        role="user",
        parts=[types.Part(text=prompt_text)]
    )

    # Stream agent events via ADK Runner
    events = []
    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg
    ):
        events.append(event)
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                final_text = "".join(part.text for part in event.content.parts if part.text)

    # Assertions
    assert len(events) > 0, "Agent produced no events during execution"
    assert len(final_text) > 0, "Agent failed to return a final text response"

    # Extract tool calls from event content parts or ADK helper
    tool_calls_executed = []
    for event in events:
        if hasattr(event, "get_function_calls") and callable(event.get_function_calls):
            for fc in event.get_function_calls():
                tool_calls_executed.append(fc.name)
        elif hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    tool_calls_executed.append(part.function_call.name)

    assert "fetch_congress_signals" in tool_calls_executed, (
        f"Agent failed to invoke fetch_congress_signals tool. Found tool calls: {tool_calls_executed}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
async def test_congress_researcher_agent_synthesis():
    """Verifies that the agent output includes coherent synthesis from tools."""
    runner = InMemoryRunner(agent=congress_researcher, app_name=APP_NAME)

    user_id = "test_user"
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )

    prompt_text = (
        f"Fetch Congressional trading signals for {TEST_DATE}. For the top identified ticker, "
        "check for government contract awards and provide a short summary."
    )
    user_msg = types.Content(
        role="user",
        parts=[types.Part(text=prompt_text)]
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg
    ):
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                final_text = "".join(part.text for part in event.content.parts if part.text)

    response_lower = final_text.lower()
    assert len(final_text.split()) > 20, "Agent response was too brief"
    assert "error" not in response_lower or "no error" in response_lower