import os
from pathlib import Path
from datetime import date
import pytest

from google.adk.runners import InMemoryRunner
from google.genai import types

from congress_trades_agent.skills.congress_researcher.agent import congress_researcher

# Resolve GCP credentials path relative to workspace root
GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

# Use today's date dynamically as the live driver
TEST_DATE = date.today().isoformat()
APP_NAME = "congress_trades_agent"


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
async def test_congress_researcher_live_relative_execution():
    """Verifies that the congress_researcher agent executes live against BigQuery 
    using today's date as the dynamic analysis driver, running real net-buy signal discovery.
    """
    runner = InMemoryRunner(agent=congress_researcher, app_name=APP_NAME)

    user_id = "live_test_user"
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )

    # Formulate prompt using the dynamic live date
    prompt_text = (
        f"Perform a live scan of Congressional trading net-buy signals as of analysis date {TEST_DATE}. "
        f"Query BigQuery using the 90-day lookback window, identify the top active ticker with "
        f"real congressional buying activity, check for any associated government contract awards, "
        f"and output a detailed synthesis of your findings."
    )
    user_msg = types.Content(
        role="user",
        parts=[types.Part(text=prompt_text)]
    )

    events = []
    final_text = ""
    tool_outputs = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg
    ):
        events.append(event)
        
        # Capture tool responses for live inspection
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_response") and part.function_response:
                    tool_outputs.append(str(part.function_response.response))
                    
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                final_text = "".join(part.text for part in event.content.parts if part.text)

    print(f"\n================ [LIVE CONGRESS RESEARCHER OUTPUT ({TEST_DATE})] ================")
    print(final_text)

    print("\n================ [LIVE TOOL DISCOVERIES INSPECTION] ================")
    if tool_outputs:
        for idx, output in enumerate(tool_outputs, 1):
            print(f"Tool Output #{idx}:\n{output}\n{'-'*50}")
    else:
        print("No tool outputs were captured during the live execution.")

    # Assertions
    assert len(events) > 0, "Agent produced no events during live execution."
    assert len(final_text) > 0, "Agent failed to return a final text response."

    # Extract executed tool names to verify real net-buy query invocation
    tool_calls_executed = []
    for event in events:
        if hasattr(event, "get_function_calls") and callable(event.get_function_calls):
            for fc in event.get_function_calls():
                tool_calls_executed.append(fc.name)
        elif hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_call") and part.function_call:
                    tool_calls_executed.append(part.function_call.name)

    print(f"\n[Verified Tool Calls Executed]: {tool_calls_executed}")
    
    # Ensure it actually invoked the net-buy signal tool rather than hallucinating
    assert any("fetch" in tool.lower() or "signal" in tool.lower() for tool in tool_calls_executed), (
        f"Agent failed to invoke expected BQ fetching tools. Found tool calls: {tool_calls_executed}"
    )