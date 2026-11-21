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

triple_agent_evaluation_metric = GEval(
    name="Live 3-Agent Confluence & Trade Synthesis Metric",
    criteria="""
1. STRICT TRUTHFULNESS: Verify that summaries and trade decisions derived from live BigQuery data accurately reflect actual congressional, insider, contract, or fundamental signals without fabricating transactions, dollar volumes, or metrics.
2. CROSS-AGENT CONSISTENCY: Ensure that InsiderAnalyst aligns with CongressResearcher, and CongressTrader's decision/rationale aligns with the retrieved confluence and fundamental context.
3. GOVERNANCE & NO PHANTOM ENTITIES: Ensure CongressTrader does not invent tickers or execute a trade when confluence signals are absent, and only cites entities present in retrieval context.
""",
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=TRUSTWORTHY_SCORE_THRESHOLD,
    model=gemini_evaluator,
)

MULTI_AGENT_SCENARIOS = [
    ("tsm_congress_and_insider", "TSM", "2026-10-07"),
    ("cdns_triple_confluence", "CDNS", "2026-10-01"),
    ("ibm_congress_and_contracts", "IBM", "2026-10-06"),
]


def _format_response(resp: object) -> str:
    return json.dumps(resp, default=str) if isinstance(resp, dict) else str(resp)


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing credentials for live BigQuery execution",
)
@pytest.mark.parametrize("scenario_name, ticker, analysis_date", MULTI_AGENT_SCENARIOS)
@patch("congress_trades_agent.skills.congress_trader.tools.store_trade_decision")
@patch("congress_trades_agent.skills.congress_trader.tools.fetch_historical_episodes")
async def test_triple_agent_live_execution_with_evaluation(
    mock_fetch_episodes,
    mock_store_decision,
    scenario_name,
    ticker,
    analysis_date,
):
    """Executes CongressResearcher, InsiderAnalyst, and CongressTrader across a shared session
    on live BigQuery data and evaluates the combined output with GEval.
    """
    mock_store_decision.return_value = "Successfully validated and stored decision record (Mocked)"
    mock_fetch_episodes.return_value = []

    user_id = f"live_eval_user_{scenario_name}"

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

    # --- STEP 1: Execute CongressResearcher ---
    congress_runner = Runner(
        agent=congress_researcher,
        app_name=APP_NAME,
        session_service=shared_session_service,
    )
    congress_prompt = (
        f"Analyze Congressional disclosures and federal contracts for ticker {ticker} "
        f"as of analysis date {analysis_date}."
    )
    congress_text = ""
    async for event in congress_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=congress_prompt)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_response", None) and part.function_response.response is not None:
                    tool_outputs.append(_format_response(part.function_response.response))
        if event.is_final_response() and event.content and event.content.parts:
            congress_text = "".join(part.text for part in event.content.parts if part.text)

    assert len(congress_text) > 20, f"CongressResearcher commentary for {ticker} was too brief."

    # --- STEP 2: Execute InsiderAnalyst ---
    insider_runner = Runner(
        agent=insider_analyst,
        app_name=APP_NAME,
        session_service=shared_session_service,
    )
    insider_prompt = (
        f"Analyze Form 4 corporate insider trading and lobbying spend for ticker {ticker} "
        f"as of analysis date {analysis_date}."
    )
    insider_text = ""
    async for event in insider_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=types.Content(role="user", parts=[types.Part(text=insider_prompt)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_response", None) and part.function_response.response is not None:
                    tool_outputs.append(_format_response(part.function_response.response))
        if event.is_final_response() and event.content and event.content.parts:
            insider_text = "".join(part.text for part in event.content.parts if part.text)

    assert len(insider_text) > 20, f"InsiderAnalyst commentary for {ticker} was too brief."

    # --- STEP 3: Execute CongressTrader ---
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
        new_message=types.Content(role="user", parts=[types.Part(text=trader_prompt)]),
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_call", None) and getattr(part.function_call, "name", None):
                    trader_tool_calls.append(part.function_call.name)
                if getattr(part, "function_response", None) and part.function_response.response is not None:
                    tool_outputs.append(_format_response(part.function_response.response))
        if event.is_final_response() and event.content and event.content.parts:
            trader_text = "".join(part.text for part in event.content.parts if part.text)

    assert len(trader_text) > 20, f"CongressTrader output for {ticker} was too brief."
    assert trader_tool_calls and trader_tool_calls[0] == "get_confluence_report", (
        f"Expected get_confluence_report first, got {trader_tool_calls}"
    )

    combined_output = (
        f"Congress Analysis:\n{congress_text}\n\n"
        f"Insider/Lobbying Analysis:\n{insider_text}\n\n"
        f"Trade Decision:\n{trader_text}"
    )

    test_case = LLMTestCase(
        input=f"3-agent live analysis for {ticker} on {analysis_date}",
        actual_output=combined_output,
        retrieval_context=tool_outputs if tool_outputs else ["Live BigQuery execution payload"],
    )

    triple_agent_evaluation_metric.measure(test_case)

    print(f"\n[GEval Score for {scenario_name}]: {triple_agent_evaluation_metric.score}")
    print(f"[GEval Reason]: {triple_agent_evaluation_metric.reason}")

    assert triple_agent_evaluation_metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, (
        f"Live 3-agent execution for {scenario_name} failed evaluation "
        f"with score {triple_agent_evaluation_metric.score}.\nReason: {triple_agent_evaluation_metric.reason}"
    )