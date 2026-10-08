import os
from pathlib import Path
import pytest

from google.adk.runners import InMemoryRunner
from google.genai import types

from congress_trades_agent.skills.insider_analyst.agent import insider_analyst

GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

TEST_DATE = "2026-09-14"
TEST_TICKER = "JEF"
APP_NAME = "congress_trades_agent"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
async def test_insider_analyst_agent_execution():
    """Verifies ADK insider_analyst agent execution, tool calls, and session state updates."""
    runner = InMemoryRunner(agent=insider_analyst, app_name=APP_NAME)

    user_id = "test_user"
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )

    # Initialize shared pipeline state on the live ADK Session
    session.state["confluence_reports"] = {}
    await runner.session_service.update_session(session)

    prompt_text = (
        f"Analyze Form 4 insider trading activity and lobbying spend for ticker {TEST_TICKER} "
        f"up to analysis date {TEST_DATE}."
    )
    user_msg = types.Content(
        role="user",
        parts=[types.Part(text=prompt_text)]
    )

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

    assert len(events) > 0, "Agent produced no events during execution"
    assert len(final_text) > 0, "Agent failed to return a final text response"

    # Extract all executed tool calls across events
    tool_calls_executed = []
    for event in events:
        if hasattr(event, "get_function_calls") and callable(event.get_function_calls):
            for fc in event.get_function_calls():
                tool_calls_executed.append(fc.name)
        elif hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    tool_calls_executed.append(part.function_call.name)

    # Verify tool execution
    assert "fetch_form4_signals" in tool_calls_executed, (
        f"Agent failed to invoke fetch_form4_signals tool. Found tool calls: {tool_calls_executed}"
    )

    # Verify real ADK Session state mutation via ToolContext
    updated_session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session.id
    )
    confluence_reports = updated_session.state.get("confluence_reports", {})
    assert TEST_TICKER in confluence_reports, (
        f"Session state 'confluence_reports' was not populated for {TEST_TICKER}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
async def test_insider_analyst_agent_synthesis():
    """Verifies that the agent output includes coherent synthesis from insider tools."""
    runner = InMemoryRunner(agent=insider_analyst, app_name=APP_NAME)

    user_id = "test_user"
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )

    session.state["confluence_reports"] = {}
    await runner.session_service.update_session(session)

    prompt_text = (
        f"Fetch Corporate Insider Form 4 signals and lobbying activity for {TEST_TICKER} "
        f"as of {TEST_DATE} and provide a concise summary of executive buying or lobbying spend."
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