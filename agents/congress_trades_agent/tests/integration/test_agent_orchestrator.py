import json
import os
from pathlib import Path
import re
from unittest.mock import patch
import pytest

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.models import GeminiModel

from congress_trades_agent.congress_agents import CONGRESS_PIPELINE

GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(
    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GEMINI_API_KEY")
)

APP_NAME = "congress_trades_agent"
TRUSTWORTHY_SCORE_THRESHOLD = 0.85

NON_TICKER_TOKENS = {
    "BUY",
    "SELL",
    "HOLD",
    "PASS",
    "THE",
    "AND",
    "FOR",
    "WITH",
    "FROM",
    "STEP",
    "JSON",
    "SQL",
    "API",
    "USD",
    "YYYY",
    "MM",
    "DD",
    "PE",
    "FCF",
    "ROE",
    "EMPTY",
    "CONFLUENCE",
    "STATUS",
    "ACTION",
    "NONE",
    "TRUE",
    "FALSE",
}

gemini_evaluator = GeminiModel(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)

orchestrator_integration_metric = GEval(
    name="Congress Orchestrator Date-Driven Integration Metric",
    criteria="""
1. SIGNAL GROUNDING: Verify that candidate selection, research summaries, and trade synthesis accurately reflect retrieved BigQuery congressional, contract, Form 4 insider, lobbying, and fundamental signals without fabricating tickers, dollar amounts, or metrics.
2. ORCHESTRATION & CONSISTENCY: Confirm the pipeline evaluated active signals for the requested analysis_date and maintained consistent ticker/date context across research, insider analysis, and trade synthesis.
3. NO PHANTOM ENTITIES: Ensure no invented tickers, executives, or unsupported transactions appear outside the retrieved tool/session context.
""",
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=TRUSTWORTHY_SCORE_THRESHOLD,
    model=gemini_evaluator,
)

ORCHESTRATOR_DATE_SCENARIOS = [
    ("date_2026_05_11_active", "2026-05-11"),
    ("date_2026_10_23_active", "2026-10-23"),
]


def _serialize_response(resp: object) -> str:
    if isinstance(resp, (dict, list)):
        return json.dumps(resp, default=str)
    return str(resp)


def _to_pretty_json(payload: object) -> str:
    """Formats dicts/lists/JSON-strings as indented JSON; falls back to raw string."""
    if isinstance(payload, (dict, list)):
        return json.dumps(payload, indent=2, default=str)
    if isinstance(payload, str):
        stripped = payload.strip()
        if stripped.startswith(("{", "[")):
            try:
                parsed = json.loads(stripped)
                return json.dumps(parsed, indent=2, default=str)
            except json.JSONDecodeError:
                pass
        return payload
    return str(payload)


def _extract_candidate_tickers(text: str) -> set[str]:
    matches = set(re.findall(r"\b[A-Z]{1,5}\b", text))
    return {tok for tok in matches if tok not in NON_TICKER_TOKENS}


def _assert_expected_agent_order(tool_calls: list[str]) -> None:
    expected_sequence = ["CongressResearcher", "InsiderAnalyst", "CongressTrader"]
    filtered = [call for call in tool_calls if call in expected_sequence]
    assert filtered, f"Expected specialist agent calls in {tool_calls}"

    indices = [filtered.index(name) for name in expected_sequence if name in filtered]
    assert indices == sorted(indices), (
        f"Specialist agents ran out of expected order: {tool_calls}"
    )


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing GCP/Gemini credentials for live BigQuery execution",
)
@pytest.mark.parametrize("scenario_name, analysis_date", ORCHESTRATOR_DATE_SCENARIOS)
@patch("congress_trades_agent.skills.congress_trader.tools.store_trade_decision")
@patch("congress_trades_agent.skills.congress_trader.tools.fetch_historical_episodes")
async def test_congress_orchestrator_by_analysis_date(
    mock_fetch_episodes,
    mock_store_decision,
    scenario_name,
    analysis_date,
):
    """Runs CONGRESS_PIPELINE driven by analysis_date against live BigQuery data,
    printing raw/JSON tool payloads and session state for inspection.
    """
    mock_store_decision.return_value = "Successfully validated and stored decision record (Mocked)"
    mock_fetch_episodes.return_value = []

    user_id = f"orch_date_user_{scenario_name}"
    session_state = {
        "candidates": [],
        "confluence_reports": {},
        "congressional_context": {},
        "insider_context": {},
    }

    session_service = InMemorySessionService()
    session = await session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        state=session_state,
    )

    runner = Runner(
        agent=CONGRESS_PIPELINE,
        app_name=APP_NAME,
        session_service=session_service,
    )

    prompt = (
        f"Run the full congressional and insider trade analysis pipeline for "
        f"analysis_date {analysis_date}. Discover active candidate tickers from the signals "
        f"and synthesize the trade evaluation."
    )

    final_text = ""
    tool_calls: list[str] = []
    tool_outputs: list[str] = []

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=prompt)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                fn_call = getattr(part, "function_call", None)
                if fn_call and getattr(fn_call, "name", None):
                    tool_calls.append(fn_call.name)
                    print(f"\n[{scenario_name}] -> FUNCTION CALL: {fn_call.name}")
                    if getattr(fn_call, "args", None):
                        print(_to_pretty_json(dict(fn_call.args)))

                fn_resp = getattr(part, "function_response", None)
                if fn_resp and fn_resp.response is not None:
                    serialized = _serialize_response(fn_resp.response)
                    tool_outputs.append(serialized)
                    resp_name = getattr(fn_resp, "name", None) or "unknown_tool"
                    print(f"\n[{scenario_name}] <- FUNCTION RESPONSE ({resp_name}):")
                    print(_to_pretty_json(fn_resp.response))

        if event.is_final_response() and event.content and event.content.parts:
            final_text = "".join(part.text for part in event.content.parts if part.text)

    updated_session = await session_service.get_session(
        app_name=APP_NAME,
        user_id=user_id,
        session_id=session.id,
    )

    print(f"\n================ [{scenario_name}] TOOL CALL SEQUENCE ================")
    print(json.dumps(tool_calls, indent=2))

    print(f"\n================ [{scenario_name}] ALL TOOL OUTPUTS ================")
    for idx, raw_out in enumerate(tool_outputs, start=1):
        print(f"--- Tool Output #{idx} ---")
        print(_to_pretty_json(raw_out))

    if updated_session and getattr(updated_session, "state", None):
        print(f"\n================ [{scenario_name}] SESSION STATE SNAPSHOT ================")
        print(_to_pretty_json(dict(updated_session.state)))

    print(f"\n================ [{scenario_name}] FINAL AGENT OUTPUT ================")
    print(_to_pretty_json(final_text))

    discovered_tickers = _extract_candidate_tickers(final_text)
    tool_context_blob = "\n".join(tool_outputs)
    tool_tickers = _extract_candidate_tickers(tool_context_blob)

    assert len(final_text) > 30, f"Orchestrator output too brief for analysis_date {analysis_date}"
    assert tool_outputs, f"Expected tool outputs from specialist agents for analysis_date {analysis_date}"
    _assert_expected_agent_order(tool_calls)

    assert discovered_tickers, (
        f"Expected at least one discovered ticker symbol in output for {analysis_date}"
    )
    if tool_tickers:
        overlap = discovered_tickers & tool_tickers
        assert overlap, (
            f"Discovered tickers {sorted(discovered_tickers)} did not overlap with "
            f"tool-returned tickers {sorted(tool_tickers)} for {analysis_date}"
        )

    test_case = LLMTestCase(
        input=prompt,
        actual_output=final_text,
        retrieval_context=tool_outputs,
    )

    orchestrator_integration_metric.measure(test_case)
    print(f"\n[{scenario_name}] GEval Score: {orchestrator_integration_metric.score}")
    print(f"[{scenario_name}] GEval Reason: {orchestrator_integration_metric.reason}")

    assert orchestrator_integration_metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, (
        f"Orchestrator integration failed for {scenario_name} ({analysis_date}) "
        f"with score {orchestrator_integration_metric.score}:\n{orchestrator_integration_metric.reason}"
    )