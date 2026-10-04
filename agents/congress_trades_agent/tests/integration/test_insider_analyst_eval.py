import json
import os
import pytest
from unittest.mock import patch
from google.genai import types
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.models import GeminiModel

from congress_trades_agent.schemas import InsiderContextPayload
from congress_trades_agent.skills.insider_analyst.agent import insider_analyst
from google.adk.runners import InMemoryRunner

APP_NAME = "congress_trades_agent"
TRUSTWORTHY_SCORE_THRESHOLD = 0.85

HAS_GCP_CREDS = bool(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GEMINI_API_KEY")
)

gemini_evaluator = GeminiModel(
    model="gemini-3.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)

insider_relevance_metric = GEval(
    name="Corporate Insider Signal Relevance & Accuracy",
    criteria="""
    1. Accurately summarize corporate insider trading activity (Form 4 filings, buy/sell ratios, net shares acquired, transaction amounts) matching RETRIEVAL_CONTEXT.
    2. Correctly identify insider executive roles (e.g., CEO, CFO, 10% owners) and flag significant cluster buying or unusual selling patterns.
    3. Maintain an authoritative, structured Quantitative Equity Analyst tone and structure output appropriately according to schema.
    4. Handle empty or zero insider activity contexts gracefully without hallucinating non-existent insider transactions.
    """,
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=TRUSTWORTHY_SCORE_THRESHOLD,
    model=gemini_evaluator,
)

INSIDER_STRESS_SCENARIOS = [
    (
        "ceo_cluster_buying",
        [
            {
                "signal_date": "2026-07-01",
                "ticker": "AAPL",
                "insider_title": "Chief Executive Officer",
                "transaction_type": "P_Purchase",
                "shares_traded": 50000,
                "transaction_value_usd": 11500000,
                "net_shares_acquired": 50000,
            }
        ],
        "Summarize corporate insider trading activity and sentiment context for 2026-07-01.",
    ),
    (
        "zero_insider_activity",
        [],
        "Summarize corporate insider trading activity and sentiment context for 2026-07-01.",
    ),
    (
        "routine_option_exercise_selling",
        [
            {
                "signal_date": "2026-07-01",
                "ticker": "MSFT",
                "insider_title": "Director",
                "transaction_type": "S_Sale",
                "shares_traded": 10000,
                "transaction_value_usd": 4500000,
                "net_shares_acquired": -10000,
            }
        ],
        "Summarize corporate insider trading activity and sentiment context for 2026-07-01.",
    ),
]


@pytest.mark.asyncio
@pytest.mark.eval
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Evaluation test skipped: missing credentials",
)
@pytest.mark.parametrize("scenario_name, mock_bq_data, prompt_text", INSIDER_STRESS_SCENARIOS)
@patch("congress_trades_agent.skills.insider_analyst.tools.get_bq_data")
async def test_eval_insider_analyst_scenarios(
    mock_get_bq_data, scenario_name, mock_bq_data, prompt_text
):
    """Evaluates InsiderAnalyst output accuracy across mocked scenario data."""
    mock_get_bq_data.return_value = mock_bq_data
    user_id = "test_user"

    runner = InMemoryRunner(agent=insider_analyst, app_name=APP_NAME)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id=user_id
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt_text)],
    )

    tool_outputs = [json.dumps(mock_bq_data)]

    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_response") and part.function_response:
                    tool_outputs.append(str(part.function_response.response))

    updated_session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session.id
    )

    raw_insider_context = updated_session.state.get("insider_context")
    assert raw_insider_context is not None, "insider_context was not found in session.state"

    if isinstance(raw_insider_context, str):
        clean_json = raw_insider_context.strip().removeprefix("```json").removeprefix("```").removesuffix("```").strip()
        payload_dict = json.loads(clean_json)
    elif isinstance(raw_insider_context, dict):
        payload_dict = raw_insider_context
    else:
        payload_dict = raw_insider_context.model_dump() if hasattr(raw_insider_context, "model_dump") else dict(raw_insider_context)

    validated_payload = InsiderContextPayload.model_validate(payload_dict)

    if not mock_bq_data:
        assert len(validated_payload.primary_tickers) == 0, "Zero activity scenario should produce empty primary_tickers."
    else:
        assert len(validated_payload.primary_tickers) > 0, "Expected primary_tickers to be populated."

    retrieval_context_payload = tool_outputs if tool_outputs else ["No context found."]
    actual_output_str = json.dumps(validated_payload.model_dump(), indent=2)

    test_case = LLMTestCase(
        input=prompt_text,
        actual_output=actual_output_str,
        retrieval_context=retrieval_context_payload,
    )

    insider_relevance_metric.measure(test_case)

    print(f"\n--- Scenario Results: {scenario_name} ---")
    print(f"[GEval Score]: {insider_relevance_metric.score}")
    print(f"[GEval Reason]: {insider_relevance_metric.reason}")

    assert insider_relevance_metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, (
        f"Scenario '{scenario_name}' failed evaluation with score {insider_relevance_metric.score}. "
        f"Reason: {insider_relevance_metric.reason}"
    )