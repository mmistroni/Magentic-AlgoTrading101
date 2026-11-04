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

# Metric focused on checking that the narrative rationale aligns logically with the decision and conviction score
trader_rationale_alignment_metric = GEval(
    name="CongressTrader Rationale & Decision Alignment",
    criteria="""
1. LOGICAL CONSISTENCY: Verify that the final action (BUY, SELL, HOLD) and conviction score directly align with the arguments presented in the rationale breakdown and signal summary. 
2. RISK RECONCILIATION: If the agent chooses a HOLD or conservative stance despite positive signals, ensure the rationale explicitly justifies this caution (e.g., citing valuation caps, debt, or macro risks). If it chooses a BUY, ensure the bullish catalysts outweigh the risks.
3. TRANSPARENCY: The qualitative explanation must clearly support the quantitative conviction score without internal contradictions.
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
    """Evaluates CongressTrader decision consistency between qualitative rationale and quantitative output."""
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
    final_response_text = ""

    async for event in runner.run_async(user_id=user_id, session_id=session.id, new_message=user_message):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_response") and part.function_response:
                    tool_outputs.append(str(part.function_response.response))
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                final_response_text = "".join(part.text for part in event.content.parts if part.text)

    assert len(final_response_text) > 20, "CongressTrader final response text was empty or too brief."

    # Parse JSON output
    try:
        clean_json = final_response_text.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        payload_dict = json.loads(clean_json)
    except Exception:
        if mock_store_trade_decision.called:
            payload_dict = mock_store_trade_decision.call_args[0][0] if mock_store_trade_decision.call_args[0] else {}
        else:
            payload_dict = {"action": "HOLD", "conviction_score": 50.0}

    # Extract decision fields safely supporting dictionary structures
    if "action" in payload_dict:
        decision_action = payload_dict["action"]
        conviction_score = payload_dict.get("conviction_score", 50.0)
    elif "decisions" in payload_dict and payload_dict["decisions"]:
        decision_action = payload_dict["decisions"][0].get("action", "HOLD")
        conviction_score = payload_dict["decisions"][0].get("conviction_score", 50.0)
    else:
        decision_action = "HOLD"
        conviction_score = 50.0

    print(f"\n[Agent Decision Output for {scenario_name}] Action: {decision_action} | Conviction: {conviction_score}")
    if "rationale" in payload_dict:
        print(f"[Rationale Summary]: {json.dumps(payload_dict['rationale'], indent=2)}")

    # Programmatic consistency check between action and conviction score
    if decision_action in ["BUY", "STRONG_BUY"]:
        assert conviction_score >= 40.0, f"BUY action requires a reasonable conviction score, got {conviction_score}"
    elif decision_action in ["SELL", "STRONG_SELL"]:
        assert conviction_score <= 60.0, f"SELL action should reflect lower conviction scores, got {conviction_score}"

    # Run GEval Rationale & Alignment Metric
    test_case = LLMTestCase(
        input=prompt_text,
        actual_output=final_response_text,
        retrieval_context=tool_outputs,
    )
    trader_rationale_alignment_metric.measure(test_case)

    print(f"[GEval Rationale Alignment Score]: {trader_rationale_alignment_metric.score}")
    print(f"[GEval Reason]: {trader_rationale_alignment_metric.reason}")

    assert trader_rationale_alignment_metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, (
        f"Scenario '{scenario_name}' failed rationale alignment evaluation with score {trader_rationale_alignment_metric.score}. "
        f"Reason: {trader_rationale_alignment_metric.reason}"
    )