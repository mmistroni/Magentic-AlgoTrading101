# agents/congress_trades_agent/tests/integration/test_insider_analyst_tool_integration.py

import os
import pytest
from google.genai import types
from google.adk.runners import InMemoryRunner

from congress_trades_agent.skills.insider_analyst.agent import insider_analyst

APP_NAME = "congress_trades_agent"

HAS_GCP_CREDS = bool(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GEMINI_API_KEY")
)

# Test matrix based on your BigQuery dataset results
INTEGRATION_TEST_SCENARIOS = [
    {
        "scenario_id": "insider_only_jef",
        "ticker": "JEF",
        "prompt": "Get insider trading activity and Form 4 transactions for ticker JEF.",
        "expected_tools": ["fetch_form4_signals"], # Adjust function name to match your tool
    },
    {
        "scenario_id": "lobbying_only_wynn",
        "ticker": "WYNN",
        "prompt": "Get lobbying spending and disclosure signals for ticker WYNN.",
        "expected_tools": ["fetch_lobbying_signals"], # Adjust function name to match your tool
    },
    {
        "scenario_id": "combined_signals_jef",
        "ticker": "JEF",
        "prompt": "Cross-reference Form 4 insider transactions with lobbying disclosures for ticker JEF.",
        "expected_tools": ["fetch_form4_signals", "fetch_lobbying_signals"],
    },
]


@pytest.mark.asyncio
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Skipped: GOOGLE_APPLICATION_CREDENTIALS or GEMINI_API_KEY required for live BigQuery execution",
)
@pytest.mark.parametrize("scenario", INTEGRATION_TEST_SCENARIOS)
async def test_insider_analyst_tool_execution(scenario):
    """Verifies tools are invoked, BigQuery returns non-empty data, and final text is returned."""
    user_id = f"test_user_{scenario['scenario_id']}"

    runner = InMemoryRunner(agent=insider_analyst, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=scenario["prompt"])],
    )

    executed_tool_calls = []
    tool_responses = []
    final_text = ""

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                # Capture tool function calls initiated by the agent
                if hasattr(part, "function_call") and part.function_call:
                    executed_tool_calls.append(part.function_call.name)

                # Capture responses returned from BigQuery tool executions
                if hasattr(part, "function_response") and part.function_response:
                    resp_data = part.function_response.response
                    tool_responses.append(resp_data)

        # Capture agent's final text response
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                final_text = "".join(part.text for part in event.content.parts if part.text)

    # 1. Assert that the agent invoked at least one tool
    assert len(executed_tool_calls) > 0, (
        f"Scenario '{scenario['scenario_id']}' failed: No tools were called by insider_analyst."
    )

    # 2. Assert that expected tools were called
    for expected_tool in scenario["expected_tools"]:
        assert any(expected_tool in tool_name for tool_name in executed_tool_calls), (
            f"Scenario '{scenario['scenario_id']}' failed: Expected tool '{expected_tool}' was not called. "
            f"Executed tools: {executed_tool_calls}"
        )

    # 3. Assert tool execution returned actual data payloads from BigQuery
    assert len(tool_responses) > 0, (
        f"Scenario '{scenario['scenario_id']}' failed: Tools were called but returned no data responses."
    )

    # 4. Assert that final text response is non-empty
    assert len(final_text.strip()) > 0, (
        f"Scenario '{scenario['scenario_id']}' failed: Agent produced an empty final response."
    )

    print(f"\n[SUCCESS] Scenario: {scenario['scenario_id']}")
    print(f"  - Tools Executed: {executed_tool_calls}")
    print(f"  - Tool Responses Received: {len(tool_responses)}")
    print(f"  - Final Response Length: {len(final_text)} chars")