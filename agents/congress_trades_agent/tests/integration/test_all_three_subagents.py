import json
import os
from pathlib import Path
from unittest.mock import patch
import pytest

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.models import GeminiModel

from congress_trades_agent.skills.congress_researcher.agent import congress_researcher
from congress_trades_agent.skills.insider_analyst.agent import insider_analyst
from congress_trades_agent.skills.congress_trader.agent import congress_trader

GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(
    os.environ.get("GOOGLE_APPLICATION_CREDENTIALS") or os.environ.get("GEMINI_API_KEY")
)

APP_NAME = "congress_trades_agent"
TRUSTWORTHY_SCORE_THRESHOLD = 0.85

gemini_evaluator = GeminiModel(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)

three_agent_integration_metric = GEval(
    name="Three-Agent BigQuery Grounding & Decision Synthesis Metric",
    criteria="""
1. SIGNAL GROUNDING: Verify that summaries and trade recommendations accurately reflect the retrieved congressional, contract, Form 4 insider, lobbying, and fundamental signals without fabricating figures or trades.
2. CROSS-AGENT COHERENCE: Ensure InsiderAnalyst aligns with CongressResearcher for the target ticker and date, and CongressTrader's action, conviction, valuation, and rationale are consistent with the gathered context.
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

# Verified (scenario_name, ticker, analysis_date) windows from BigQuery discovery query
BQ_VERIFIED_SCENARIOS = [
    ("tsm_oct_2026", "TSM", "2026-10-23"),
    ("rmd_jul_2026", "RMD", "2026-07-21"),
    ("spgi_may_2026", "SPGI", "2026-05-11"),
]


def _serialize_response(resp: object) -> str:
    if isinstance(resp, dict):
        return json.dumps(resp, default=str)
    return str(resp)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing GCP/Gemini credentials for live BigQuery execution",
)
@pytest.mark.parametrize("scenario_name, ticker, analysis_date", BQ_VERIFIED_SCENARIOS)
@patch("congress_trades_agent.skills.congress_trader.tools.store_trade_decision")
@patch("congress_trades_agent.skills.congress_trader.tools.fetch_historical_episodes")
async def test_three_agent_integration_on_verified_bq_windows(
    mock_fetch_episodes,
    mock_store_decision,
    scenario_name,
    ticker,
    analysis_date,
):
    """Runs CongressResearcher -> InsiderAnalyst -> CongressTrader over a shared session
    for BigQuery-verified active windows and evaluates grounding with GEval.
    """
    mock_store_decision.return_value = "Successfully validated and stored decision record (Mocked)"
    mock_fetch_episodes.return_value = []

    user_id = f"three_agent_bq_{scenario_name}"
    session_state = {
        "candidates": [],
        "confluence_reports": {},
        "congressional_context": {},
        "insider_context": {},
    }

    shared_session_service = InMemorySessionService()
    session = await shared_session_service.create_session(
        app_name=APP_NAME,
        user_id=user_id,
        state=session_state,
    )

    tool_outputs: list[str] = []

    # 1. CongressResearcher
    researcher_runner = Runner(
        agent=congress_researcher,
        app_name=APP_NAME,
        session_service=shared_session_service,
    )
    researcher_prompt = (
        f"Analyze Senate disclosures and federal contract signals for ticker {ticker} "
        f"as of analysis_date {analysis_date} (90-day lookback)."
    )
    researcher_text = ""
    async for event in researcher_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=researcher_prompt)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_response", None) and part.function_response.response is not None:
                    tool_outputs.append(_serialize_response(part.function_response.response))
        if event.is_final_response() and event.content and event.content.parts:
            researcher_text = "".join(part.text for part in event.content.parts if part.text)

    assert len(researcher_text) > 20, f"CongressResearcher output too brief for {ticker} @ {analysis_date}"

    # 2. InsiderAnalyst
    insider_runner = Runner(
        agent=insider_analyst,
        app_name=APP_NAME,
        session_service=shared_session_service,
    )
    insider_prompt = (
        f"Analyze Form 4 insider transactions and lobbying signals for ticker {ticker} "
        f"as of analysis_date {analysis_date}."
    )
    insider_text = ""
    async for event in insider_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=insider_prompt)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_response", None) and part.function_response.response is not None:
                    tool_outputs.append(_serialize_response(part.function_response.response))
        if event.is_final_response() and event.content and event.content.parts:
            insider_text = "".join(part.text for part in event.content.parts if part.text)

    assert len(insider_text) > 20, f"InsiderAnalyst output too brief for {ticker} @ {analysis_date}"

    # 3. CongressTrader
    trader_runner = Runner(
        agent=congress_trader,
        app_name=APP_NAME,
        session_service=shared_session_service,
    )
    trader_prompt = (
        f"Perform a comprehensive trade evaluation and synthesize a final decision record "
        f"for ticker {ticker} as of analysis date {analysis_date}."
    )
    trader_text = ""
    trader_tool_calls: list[str] = []
    async for event in trader_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part.from_text(text=trader_prompt)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_call", None) and getattr(part.function_call, "name", None):
                    trader_tool_calls.append(part.function_call.name)
                if getattr(part, "function_response", None) and part.function_response.response is not None:
                    tool_outputs.append(_serialize_response(part.function_response.response))
        if event.is_final_response() and event.content and event.content.parts:
            trader_text = "".join(part.text for part in event.content.parts if part.text)

    assert len(trader_text) > 20, f"CongressTrader output too brief for {ticker} @ {analysis_date}"
    assert trader_tool_calls and trader_tool_calls[0] == "get_confluence_report", (
        f"Expected get_confluence_report first, got {trader_tool_calls}"
    )

    combined_output = (
        f"Congress Researcher:\n{researcher_text}\n\n"
        f"Insider Analyst:\n{insider_text}\n\n"
        f"Congress Trader:\n{trader_text}"
    )

    test_case = LLMTestCase(
        input=f"3-agent evaluation for {ticker} on {analysis_date}",
        actual_output=combined_output,
        retrieval_context=tool_outputs or ["Live BigQuery execution payload"],
    )

    three_agent_integration_metric.measure(test_case)

    print(f"\n[{scenario_name}] GEval Score: {three_agent_integration_metric.score}")
    print(f"[{scenario_name}] GEval Reason: {three_agent_integration_metric.reason}")

    assert three_agent_integration_metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, (
        f"Scenario {scenario_name} ({ticker} @ {analysis_date}) failed GEval "
        f"({three_agent_integration_metric.score}): {three_agent_integration_metric.reason}"
    )