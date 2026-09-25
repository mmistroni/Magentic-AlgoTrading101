import json
import os
import pytest
from unittest.mock import patch
from google.genai import types
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

# Correct DeepEval import
from deepeval.models import GeminiModel

# Import agent and runner components
from congress_trades_agent.skills.congress_researcher.agent import congress_researcher
from google.adk.runners import InMemoryRunner

APP_NAME = "congress_trades_agent"
TRUSTWORTHY_SCORE_THRESHOLD = 0.85

HAS_GCP_CREDS = bool(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GEMINI_API_KEY")
)

# Instantiate GeminiModel with Gemini 2.5 Flash / 3 Flash target
gemini_evaluator = GeminiModel(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)

# Define evaluation metric with RETRIEVAL_CONTEXT
political_relevance_metric = GEval(
    name="Political Strategy Relevance & Accuracy",
    criteria="""
    1. Accurately summarize the congressional trading signals matching RETRIEVAL_CONTEXT (tickers, buy/sell counts, net buys, or structured response objects).
    2. Correctly incorporate the broader market regime context (e.g., market uptrend or downtrend) provided in RETRIEVAL_CONTEXT.
    3. Maintain an authoritative, structured Washington Policy Strategist tone and structure output appropriately according to schema.
    4. Handle empty trading contexts gracefully without hallucinating non-existent congressional trades.
    """,
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=TRUSTWORTHY_SCORE_THRESHOLD,
    model=gemini_evaluator,
)

STRESS_SCENARIOS = [
    (
        "high_conviction_defense",
        [
            {
                "signal_date": "2026-07-01",
                "ticker": "LMT",
                "purchase_count": 6,
                "sale_count": 0,
                "net_buy_activity": 6,
                "buying_days_count": 3,
                "last_trade_date": "2026-06-28",
                "market_uptrend": True,
            }
        ],
        "Summarize congressional trading activity and political context for 2026-07-01.",
    ),
    (
        "zero_activity_day",
        [],
        "Summarize congressional trading activity and political context for 2026-07-01.",
    ),
    (
        "divergent_market_downtrend",
        [
            {
                "signal_date": "2026-07-01",
                "ticker": "NVDA",
                "purchase_count": 4,
                "sale_count": 0,
                "net_buy_activity": 4,
                "buying_days_count": 2,
                "last_trade_date": "2026-06-29",
                "market_uptrend": False,
            }
        ],
        "Summarize congressional trading activity and political context for 2026-07-01.",
    ),
]


@pytest.mark.asyncio
@pytest.mark.eval
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Evaluation test skipped: missing credentials",
)
@pytest.mark.parametrize("scenario_name, mock_bq_data, prompt_text", STRESS_SCENARIOS)
@patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_data")
async def test_eval_congress_researcher_scenarios(
    mock_get_bq_data, scenario_name, mock_bq_data, prompt_text
):
    """Evaluates CongressResearcher output accuracy across mocked scenario data."""
    mock_get_bq_data.return_value = mock_bq_data
    user_id = "test_user"

    runner = InMemoryRunner(agent=congress_researcher, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt_text)],
    )

    final_text = ""
    tool_outputs = [json.dumps(mock_bq_data)]  # Include the input signal data

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        # Dynamically record tool execution responses as retrieval context
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_response") and part.function_response:
                    tool_outputs.append(str(part.function_response.response))

        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                final_text = "".join(
                    part.text for part in event.content.parts if hasattr(part, "text") and part.text
                )

    # Now retrieval_context contains BOTH signals and real/mocked contract query outputs
    retrieval_context_payload = tool_outputs if tool_outputs else ["No context found."]

    test_case = LLMTestCase(
        input=prompt_text,
        actual_output=final_text,
        retrieval_context=retrieval_context_payload,
    )

    political_relevance_metric.measure(test_case)

    print(f"\n--- Scenario Results: {scenario_name} ---")
    print(f"[GEval Score]: {political_relevance_metric.score}")
    print(f"[GEval Reason]: {political_relevance_metric.reason}")

    assert political_relevance_metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, (
        f"Scenario '{scenario_name}' failed evaluation with score {political_relevance_metric.score}. "
        f"Reason: {political_relevance_metric.reason}"
    )