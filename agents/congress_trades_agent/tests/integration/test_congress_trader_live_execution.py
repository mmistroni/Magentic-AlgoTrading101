import json
import os
from pathlib import Path
import pytest
from unittest.mock import patch

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.models import GeminiModel

# Import your actual CongressTrader agent
from congress_trades_agent.skills.congress_trader.agent import congress_trader

GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

APP_NAME = "congress_trades_agent"
TRUSTWORTHY_SCORE_THRESHOLD = 0.85

gemini_evaluator = GeminiModel(
    model="gemini-3.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)

trader_evaluation_metric = GEval(
    name="CongressTrader Decision Synthesis & Grounding Metric",
    criteria="""
1. VALID TRADE ACTION: Verify that the agent outputs a clear structural decision containing an action (BUY, SELL, HOLD), a conviction score, and a valuation verdict.
2. DATA GROUNDING: Ensure that the rationale relies on the retrieved congressional and insider data without inventing fictitious financial metrics or trades.
3. STRUCTURE & PERSISTENCE: Check that the synthesis addresses fundamental health and congressional/insider signals coherently.
""",
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=TRUSTWORTHY_SCORE_THRESHOLD,
    model=gemini_evaluator,
)

empty_confluence_guard_metric = GEval(
    name="CongressTrader Empty Confluence Short-Circuit Metric",
    criteria="""
1. EMPTY-STATE SHORT-CIRCUIT: When get_confluence_report indicates no signals or empty confluence (has_signals is false / EMPTY_CONFLUENCE), verify the agent immediately short-circuits and refuses to synthesize or store a trade decision.
2. NO HALLUCINATED TRADES OR METRICS: Ensure the agent does NOT invent a BUY/SELL/HOLD trade action, conviction score, or fabricated fundamental/congressional/insider metrics for unapproved or unverified tickers.
3. GROUNDED EXPLANATION: Verify the response clearly explains that no active confluence candidates/signals were found in session state.
""",
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=TRUSTWORTHY_SCORE_THRESHOLD,
    model=gemini_evaluator,
)

TRADER_SCENARIOS = [
    ("trader_scenario_april_2025", "NVDA", "2025-04-01"),
    ("trader_scenario_may_2025", "AAPL", "2025-05-15"),
    ("trader_scenario_march_2026", "MSFT", "2026-03-02"),
]


def _extract_has_signals(tool_outputs: list[str]) -> bool:
    for raw in tool_outputs:
        try:
            parsed = json.loads(raw) if isinstance(raw, str) else raw
            if isinstance(parsed, dict) and "has_signals" in parsed:
                return bool(parsed["has_signals"])
        except Exception:
            if '"has_signals": true' in str(raw).lower() or "'has_signals': true" in str(raw).lower():
                return True
    return False


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing credentials for live BigQuery execution",
)
@pytest.mark.parametrize("scenario_name, ticker, analysis_date", TRADER_SCENARIOS)
@patch("congress_trades_agent.skills.congress_trader.tools.store_trade_decision")
@patch("congress_trades_agent.skills.congress_trader.tools.fetch_historical_episodes")
async def test_congress_trader_live_execution(
    mock_fetch_episodes,
    mock_store_decision,
    scenario_name,
    ticker,
    analysis_date,
):
    """Executes CongressTrader agent respecting empty confluence short-circuiting and GEval criteria."""
    mock_store_decision.return_value = "Successfully validated and stored decision record (Mocked)"
    mock_fetch_episodes.return_value = []

    user_id = f"trader_eval_user_{scenario_name}"

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

    trader_runner = Runner(
        agent=congress_trader,
        app_name=APP_NAME,
        session_service=shared_session_service,
    )

    trader_prompt = (
        f"Perform a comprehensive trade evaluation and synthesize a final decision record "
        f"for ticker {ticker} as of analysis date {analysis_date}. "
        f"Incorporate fundamentals, congressional disclosures, and insider trading signals."
    )
    user_msg = types.Content(role="user", parts=[types.Part(text=trader_prompt)])

    trader_text = ""
    tool_calls_made: list[str] = []
    tool_outputs: list[str] = []

    async for event in trader_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg,
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if getattr(part, "function_call", None) and getattr(part.function_call, "name", None):
                    tool_calls_made.append(part.function_call.name)
                if getattr(part, "function_response", None) and getattr(part.function_response, "response", None):
                    resp = part.function_response.response
                    tool_outputs.append(json.dumps(resp) if isinstance(resp, dict) else str(resp))
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                trader_text = "".join(part.text for part in event.content.parts if part.text)

    print(f"\n================ [{scenario_name.upper()}] CONGRESS TRADER OUTPUT ================")
    print(trader_text)

    assert len(trader_text) > 20, f"CongressTrader output for {ticker} was too brief."
    assert tool_calls_made and tool_calls_made[0] == "get_confluence_report", (
        f"Expected get_confluence_report first, got {tool_calls_made}"
    )

    has_signals = _extract_has_signals(tool_outputs)
    if not has_signals:
        mock_store_decision.assert_not_called()
        metric = empty_confluence_guard_metric
    else:
        metric = trader_evaluation_metric

    test_case = LLMTestCase(
        input=f"CongressTrader evaluation for {ticker} on {analysis_date} (has_signals={has_signals})",
        actual_output=trader_text,
        retrieval_context=tool_outputs if tool_outputs else ['{"has_signals": false, "status": "EMPTY_CONFLUENCE"}'],
    )

    metric.measure(test_case)

    print(f"\n[GEval ({metric.name}) Score for {scenario_name}]: {metric.score}")
    print(f"[GEval Reason]: {metric.reason}")

    assert metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, (
        f"CongressTrader execution for {scenario_name} failed evaluation "
        f"with score {metric.score}.\nReason: {metric.reason}"
    )