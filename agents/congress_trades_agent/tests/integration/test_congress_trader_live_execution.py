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

TRADER_SCENARIOS = [
    ("trader_scenario_april_2025", "NVDA", "2025-04-01"),
    ("trader_scenario_may_2025", "AAPL", "2025-05-15"),
    ("trader_scenario_march_2026", "MSFT", "2026-03-02"),
]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing credentials for live BigQuery execution",
)
@pytest.mark.parametrize("scenario_name, ticker, analysis_date", TRADER_SCENARIOS)
@patch("congress_trades_agent.skills.congress_trader.tools.store_trade_decision")  # Mock persistence
@patch("congress_trades_agent.skills.congress_trader.tools.fetch_historical_episodes")  # Mock history fetch
async def test_congress_trader_live_execution(
    mock_fetch_episodes, 
    mock_store_decision, 
    scenario_name, 
    ticker, 
    analysis_date
):
    """Executes CongressTrader agent on live BigQuery data for specific high-activity dates,
    with store and fetch strategies mocked, validates response output, and evaluates via GEval.
    """
    # 1. Configure the mocks so they don't hit the empty table or fail on DB state
    mock_store_decision.return_value = "Successfully validated and stored decision record (Mocked)"
    mock_fetch_episodes.return_value = []  # Returns empty history cleanly without throwing KeyErrors

    user_id = f"trader_eval_user_{scenario_name}"

    session_state = {
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
        session_service=shared_session_service
    )

    trader_prompt = (
        f"Perform a comprehensive trade evaluation and synthesize a final decision record "
        f"for ticker {ticker} as of analysis date {analysis_date}. "
        f"Incorporate fundamentals, congressional disclosures, and insider trading signals."
    )
    user_msg = types.Content(role="user", parts=[types.Part(text=trader_prompt)])

    trader_text = ""
    tool_outputs = []

    async for event in trader_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg,
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_response") and part.function_response:
                    tool_outputs.append(str(part.function_response.response))
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                trader_text = "".join(part.text for part in event.content.parts if part.text)

    print(f"\n================ [{scenario_name.upper()}] CONGRESS TRADER OUTPUT ================")
    print(trader_text)

    assert len(trader_text) > 20, f"CongressTrader output for {ticker} was too brief."

    # Verify that the store strategy was invoked by the agent during its execution flow (optional check)
    # assert mock_store_decision.called

    test_case = LLMTestCase(
        input=f"CongressTrader evaluation for {ticker} on {analysis_date}",
        actual_output=trader_text,
        retrieval_context=tool_outputs if tool_outputs else ["Live BigQuery execution payload"],
    )

    trader_evaluation_metric.measure(test_case)

    print(f"\n[GEval Score for {scenario_name}]: {trader_evaluation_metric.score}")
    print(f"[GEval Reason]: {trader_evaluation_metric.reason}")

    assert trader_evaluation_metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, (
        f"CongressTrader execution for {scenario_name} failed evaluation "
        f"with score {trader_evaluation_metric.score}.\nReason: {trader_evaluation_metric.reason}"
    )