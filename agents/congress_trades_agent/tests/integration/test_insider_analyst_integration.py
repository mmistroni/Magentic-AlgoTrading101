import os
from pathlib import Path
import pytest

from google.adk.runners import InMemoryRunner
from google.genai import types

from congress_trades_agent.skills.insider_analyst.agent import insider_analyst

GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

APP_NAME = "congress_trades_agent"

# All 4 integration test scenarios
INTEGRATION_SCENARIOS = [
    (
        "both_signals_present",
        "JEF",
        "2026-09-14",
        "Analyze Form 4 insider trading activity and lobbying spend for ticker JEF up to analysis date 2026-09-14.",
    ),
    (
        "insider_only",
        "TSLA",
        "2026-09-14",
        "Analyze Form 4 insider trading activity and lobbying spend for ticker TSLA up to analysis date 2026-09-14.",
    ),
    (
        "lobbying_only",
        "LMT",
        "2026-09-14",
        "Analyze Form 4 insider trading activity and lobbying spend for ticker LMT up to analysis date 2026-09-14.",
    ),
    (
        "zero_activity_both",
        "XYZNONEXISTENT",
        "2026-09-14",
        "Analyze Form 4 insider trading activity and lobbying spend for ticker XYZNONEXISTENT up to analysis date 2026-09-14.",
    ),
]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS",
)
@pytest.mark.parametrize("scenario_name, ticker, analysis_date, prompt_text", INTEGRATION_SCENARIOS)
async def test_insider_analyst_agent_execution_scenarios(scenario_name, ticker, analysis_date, prompt_text):
    """Verifies ADK insider_analyst agent execution, tool calls, and session state updates across all 4 scenarios."""
    runner = InMemoryRunner(agent=insider_analyst, app_name=APP_NAME)
    user_id = f"test_user_{scenario_name}"

    # Initialize state directly inside create_session (ADK standard pattern)
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        state={"confluence_reports": {}}
    )

    user_msg = types.Content(
        role="user",
        parts=[types.Part(text=prompt_text)],
    )

    events = []
    final_text = ""
    tool_calls_executed = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg,
    ):
        events.append(event)

        # Extract executed tool names across event types
        if hasattr(event, "get_function_calls") and callable(event.get_function_calls):
            for fc in event.get_function_calls():
                tool_calls_executed.append(fc.name)
        elif hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    tool_calls_executed.append(part.function_call.name)

        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                final_text = "".join(part.text for part in event.content.parts if part.text)

    # 1. Assert runner execution completion
    assert len(events) > 0, f"Scenario '{scenario_name}': Agent produced no events during execution"
    assert len(final_text) > 0, f"Scenario '{scenario_name}': Agent failed to return a final text response"

    # 2. Assert signal tools invocation
    assert "fetch_form4_signals" in tool_calls_executed or "fetch_lobbying_signals" in tool_calls_executed, (
        f"Scenario '{scenario_name}': Agent failed to invoke signal tools. Found tool calls: {tool_calls_executed}"
    )

    # 3. Retrieve final session state
    updated_session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session.id
    )
    confluence_reports = updated_session.state.get("confluence_reports", {})

    # 4. Scenario-specific state & output assertions
    if scenario_name != "zero_activity_both":
        assert ticker in confluence_reports, (
            f"Scenario '{scenario_name}': Session state 'confluence_reports' was not populated for {ticker}"
        )
    else:
        response_lower = final_text.lower()
        assert any(
            phrase in response_lower
            for phrase in ["no ", "zero", "none", "not found", "no insider", "no lobbying"]
        ), f"Scenario '{scenario_name}': Agent failed to report zero activity in its response."


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS",
)
async def test_insider_analyst_agent_synthesis():
    """Verifies that the agent output includes coherent synthesis from insider tools."""
    runner = InMemoryRunner(agent=insider_analyst, app_name=APP_NAME)
    user_id = "test_user_synthesis"

    ticker = INTEGRATION_SCENARIOS[0][1]
    analysis_date = INTEGRATION_SCENARIOS[0][2]

    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        state={"confluence_reports": {}}
    )

    prompt_text = (
        f"Fetch Corporate Insider Form 4 signals and lobbying activity for {ticker} "
        f"as of {analysis_date} and provide a concise summary of executive buying or lobbying spend."
    )
    user_msg = types.Content(
        role="user",
        parts=[types.Part(text=prompt_text)],
    )

    final_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg,
    ):
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                final_text = "".join(part.text for part in event.content.parts if part.text)

    response_lower = final_text.lower()
    assert len(final_text.split()) > 20, "Agent response was too brief"
    assert "error" not in response_lower or "no error" in response_lower