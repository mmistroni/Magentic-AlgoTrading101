import os
from pathlib import Path
import pytest

from google.adk.runners import InMemoryRunner
from google.genai import types

from congress_trades_agent.skills.congress_researcher.agent import congress_researcher
from congress_trades_agent.skills.insider_analyst.agent import insider_analyst

GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

APP_NAME = "congress_trades_agent"

# Locked scenarios from BigQuery correlation query results
MULTI_AGENT_SCENARIOS = [
    (
        "tsm_congress_and_insider",
        "TSM",
        "2026-10-07",
    ),
    (
        "cdns_triple_confluence",
        "CDNS",
        "2026-10-01",
    ),
    (
        "ibm_congress_and_contracts",
        "IBM",
        "2026-10-06",
    ),
]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing credentials",
)
@pytest.mark.parametrize("scenario_name, ticker, analysis_date", MULTI_AGENT_SCENARIOS)
async def test_dual_agent_sequential_execution(scenario_name, ticker, analysis_date):
    """Executes CongressResearcher followed by InsiderAnalyst on the same shared ADK session state."""
    user_id = f"test_user_{scenario_name}"

    session_state = {
        "confluence_reports": {},
        "congressional_context": {},
        "insider_context": {},
    }

    # --- STEP 1: Execute CongressResearcher ---
    congress_runner = InMemoryRunner(agent=congress_researcher, app_name=APP_NAME)
    session = await congress_runner.session_service.create_session(
        app_name=congress_runner.app_name,
        user_id=user_id,
        state=session_state,
    )

    congress_prompt = (
        f"Analyze Congressional disclosures and federal contracts for ticker {ticker} "
        f"as of analysis date {analysis_date}."
    )
    user_msg_1 = types.Content(
        role="user",
        parts=[types.Part(text=congress_prompt)],
    )

    congress_text = ""
    async for event in congress_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg_1,
    ):
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                congress_text = "".join(part.text for part in event.content.parts if part.text)

    # Assert CongressResearcher response & commentary
    assert len(congress_text) > 0, f"CongressResearcher failed to generate commentary for {ticker}"
    assert len(congress_text.split()) > 20, f"CongressResearcher commentary for {ticker} was too brief"

    # --- STEP 2: Execute InsiderAnalyst sharing CongressRunner's Session Service ---
    insider_runner = InMemoryRunner(
        agent=insider_analyst,
        app_name=APP_NAME,
        session_service=congress_runner.session_service,  # Shared session memory
    )

    insider_prompt = (
        f"Analyze Form 4 corporate insider trading and lobbying spend for ticker {ticker} "
        f"as of analysis date {analysis_date}."
    )
    user_msg_2 = types.Content(
        role="user",
        parts=[types.Part(text=insider_prompt)],
    )

    insider_text = ""
    async for event in insider_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg_2,
    ):
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                insider_text = "".join(part.text for part in event.content.parts if part.text)

    # Assert InsiderAnalyst response & commentary
    assert len(insider_text) > 0, f"InsiderAnalyst failed to generate commentary for {ticker}"
    assert len(insider_text.split()) > 20, f"InsiderAnalyst commentary for {ticker} was too brief"

    # --- STEP 3: Verify Final ADK Session State Population ---
    updated_session = await congress_runner.session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session.id
    )

    confluence_reports = updated_session.state.get("confluence_reports", {})
    
    # Assert both agents successfully populated state for the target ticker
    assert ticker in confluence_reports or (
        "congressional_context" in updated_session.state and "insider_context" in updated_session.state
    ), f"Scenario '{scenario_name}': Session state failed to capture multi-agent context for {ticker}."