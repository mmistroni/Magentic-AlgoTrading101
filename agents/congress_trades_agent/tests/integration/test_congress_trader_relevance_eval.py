import json
import os
import pytest
from unittest.mock import patch
from google.genai import types
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.models import GeminiModel

from google.adk.runners import InMemoryRunner
from congress_trades_agent.schemas import CongressTraderPayload, TickerDecisionRecord
from congress_trades_agent.skills.congress_trader.agent import congress_trader

APP_NAME = "congress_trades_agent"
TRUSTWORTHY_SCORE_THRESHOLD = 0.85

HAS_GCP_CREDS = bool(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GEMINI_API_KEY")
)

gemini_evaluator = GeminiModel(
    model="gemini-3.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)

trader_relevance_metric = GEval(
    name="CongressTrader Decision Synthesis & Grounding Metric",
    criteria="""
1. VALID TRADE ACTION: Verify that the agent outputs a clear structured decision containing an action (BUY, SELL, HOLD), conviction score, and valuation verdict matching the payload schema.
2. DATA GROUNDING: Ensure that the rationale strictly relies on the retrieved fundamental, congressional, and insider context without inventing fictitious financial metrics, stock prices, or trades.
3. STRUCTURE & PERSISTENCE: Check that the synthesis addresses fundamental health, insider activity, and congressional net-buys coherently.
""",
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=TRUSTWORTHY_SCORE_THRESHOLD,
    model=gemini_evaluator,
)

RELEVANCE_SCENARIOS = [
    (
        "high_conviction_buy",
        {
            "ticker": "NVDA",
            "fundamentals": {"price": 138.50, "pe_ratio": 31.2, "valuation_verdict": "UNDERVALUED", "fundamental_health_score": 85.0},
            "congressional": {"congressional_net_buys": 3},
            "insider": {"insider_cluster_buy": True, "net_buy_value": 5000000.0}
        },
        "Perform trade evaluation and synthesize a final decision record for NVDA as of 2026-07-01."
    ),
    (
        "conflicting_signals_hold",
        {
            "ticker": "TSLA",
            "fundamentals": {"price": 220.00, "pe_ratio": 65.0, "valuation_verdict": "OVERVALUED", "fundamental_health_score": 40.0},
            "congressional": {"congressional_net_buys": 4},
            "insider": {"insider_cluster_buy": False, "net_buy_value": -12000000.0}
        },
        "Perform trade evaluation and synthesize a final decision record for TSLA as of 2026-07-01."
    ),
]


@pytest.mark.asyncio
@pytest.mark.eval
@pytest.mark.skipif(not HAS_GCP_CREDS, reason="Evaluation test skipped: missing credentials")
@pytest.mark.parametrize("scenario_name, mock_context_data, prompt_text", RELEVANCE_SCENARIOS)
@patch("congress_trades_agent.skills.congress_trader.tools.store_trade_decision")
@patch("congress_trades_agent.skills.congress_trader.tools.fetch_historical_episodes")
async def test_eval_congress_trader_relevance(
    mock_fetch_historical_episodes,
    mock_store_trade_decision,
    scenario_name,
    mock_context_data,
    prompt_text,
):
    """Evaluates CongressTrader decision relevance and structural accuracy."""
    mock_store_trade_decision.return_value = "Successfully validated and stored record (Mocked)"
    mock_fetch_historical_episodes.return_value = []

    user_id = f"trader_rel_{scenario_name}"
    initial_session_state = {
        "confluence_reports": {mock_context_data["ticker"]: mock_context_data},
        "congressional_context": {mock_context_data["ticker"]: mock_context_data.get("congressional", {})},
        "insider_context": {mock_context_data["ticker"]: mock_context_data.get("insider", {})},
    }

    runner = InMemoryRunner(agent=congress_trader, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id, state=initial_session_state
    )

    user_message = types.Content(role="user", parts=[types.Part.from_text(text=prompt_text)])
    tool_outputs = [json.dumps(mock_context_data)]

    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=user_message):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_response") and part.function_response:
                    tool_outputs.append(str(part.function_response.response))

    updated_session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session.id
    )
    raw_decision = updated_session.state.get("trade_decision")
    assert raw_decision is not None, "trade_decision missing from session state"

    # Clean and parse JSON payload
    if isinstance(raw_decision, str):
        clean_json = raw_decision.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        payload_dict = json.loads(clean_json)
    elif hasattr(raw_decision, "model_dump"):
        payload_dict = raw_decision.model_dump()
    else:
        payload_dict = dict(raw_decision)

    # Support validation against either CongressTraderPayload or individual TickerDecisionRecord
    if "decisions" in payload_dict or isinstance(payload_dict.get("primary_tickers"), list):
        validated_payload = CongressTraderPayload.model_validate(payload_dict)
        decision_action = validated_payload.decisions[0].action.value if validated_payload.decisions else "HOLD"
    else:
        validated_decision = TickerDecisionRecord.model_validate(payload_dict)
        decision_action = validated_decision.action.value

    # Business rule assertions based on scenario
    if scenario_name == "high_conviction_buy":
        assert decision_action in ["BUY", "STRONG_BUY"]
    elif scenario_name == "conflicting_signals_hold":
        assert decision_action in ["HOLD", "SELL", "STRONG_SELL"]

    test_case = LLMTestCase(
        input=prompt_text,
        actual_output=json.dumps(payload_dict, indent=2),
        retrieval_context=tool_outputs,
    )
    trader_relevance_metric.measure(test_case)

    print(f"\n--- Relevance Scenario [{scenario_name}] Score: {trader_relevance_metric.score} ---")
    assert trader_relevance_metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, trader_relevance_metric.reason