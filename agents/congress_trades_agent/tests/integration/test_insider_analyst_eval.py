import json
import os
import pytest
from unittest.mock import patch
from google.genai import types
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.models import GeminiModel

from google.adk.runners import InMemoryRunner
from congress_trades_agent.schemas import InsiderContextPayload
from congress_trades_agent.skills.insider_analyst.agent import insider_analyst

APP_NAME = "congress_trades_agent"
TRUSTWORTHY_SCORE_THRESHOLD = 0.85

HAS_GCP_CREDS = bool(
    os.getenv("GOOGLE_APPLICATION_CREDENTIALS") or os.getenv("GEMINI_API_KEY")
)

gemini_evaluator = GeminiModel(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)

insider_relevance_metric = GEval(
    name="Corporate Insider Signal Relevance & Accuracy",
    criteria="""
1. Accurately summarize corporate insider trading activity (Form 4 filings, buy/sell ratios, net shares acquired, transaction amounts) strictly matching RETRIEVAL_CONTEXT.
2. Correctly identify insider executive roles (e.g., CEO, CFO, 10% owners) and flag significant cluster buying or unusual selling patterns when present.
3. Maintain an authoritative, structured Quantitative Equity Analyst tone and adhere strictly to the schema structure.
4. Non-Hallucination & Zero-Activity Handling:
   - When RETRIEVAL_CONTEXT is empty or contains '[]', DO NOT synthesize, invent, or search for non-existent insider transactions or unrelated lobbying signals.
   - Return empty signal containers (form4_signals, lobbying_signals, asymmetric_flags) while keeping the target ticker in primary_tickers.
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
                "ticker": "AAPL",
                "issuer": "Apple Inc.",
                "net_buy_value": 11500000.0,
                "unique_buyers": 3,
                "is_c_suite_buy": True,
                "is_cluster_buy": True,
                "buy_count": 3,
                "sell_count": 0,
                "insider_activity_score": 90.0,
            }
        ],
        "Summarize corporate insider trading activity and sentiment context for AAPL on 2026-07-01.",
    ),
    (
        "zero_insider_activity",
        [],
        "Summarize corporate insider trading activity and sentiment context for AAPL on 2026-07-01.",
    ),
    (
        "routine_selling",
        [
            {
                "ticker": "MSFT",
                "issuer": "Microsoft Corp",
                "net_buy_value": -4500000.0,
                "unique_buyers": 0,
                "is_c_suite_buy": False,
                "is_cluster_buy": False,
                "buy_count": 0,
                "sell_count": 2,
                "insider_activity_score": 10.0,
            }
        ],
        "Summarize corporate insider trading activity and sentiment context for MSFT on 2026-07-01.",
    ),
]


@pytest.mark.asyncio
@pytest.mark.eval
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Evaluation test skipped: missing credentials",
)
@pytest.mark.parametrize("scenario_name, mock_bq_data, prompt_text", INSIDER_STRESS_SCENARIOS)
@patch("congress_trades_agent.skills.insider_analyst.tools.get_lobbying_data")
@patch("congress_trades_agent.skills.insider_analyst.tools.get_form4_data")
async def test_eval_insider_analyst_scenarios(
    mock_get_form4_data,
    mock_get_lobbying_data,
    scenario_name,
    mock_bq_data,
    prompt_text,
):
    """Evaluates InsiderAnalyst output accuracy and non-hallucination across mocked scenario data."""
    # 1. Setup mock query returns for offline execution
    mock_get_form4_data.return_value = mock_bq_data
    mock_get_lobbying_data.return_value = []

    user_id = "test_user"
    runner = InMemoryRunner(agent=insider_analyst, app_name=APP_NAME)

    # 2. Seed initial state at session creation (no update_session required)
    session = await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        state={
            "confluence_reports": {},
            "insider_context": {},
        },
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt_text)],
    )

    tool_outputs = [json.dumps(mock_bq_data)]

    # 3. Execute runner & accumulate tool output responses
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_message,
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_response") and part.function_response:
                    tool_outputs.append(str(part.function_response.response))

    # 4. Extract state after agent execution completes
    updated_session = await runner.session_service.get_session(
        app_name=runner.app_name, user_id=user_id, session_id=session.id
    )

    raw_insider_context = updated_session.state.get("insider_context")
    assert raw_insider_context is not None, "insider_context was not found in session.state"

    if isinstance(raw_insider_context, str):
        clean_json = (
            raw_insider_context.strip()
            .removeprefix("```json")
            .removeprefix("```")
            .removesuffix("```")
            .strip()
        )
        payload_dict = json.loads(clean_json)
    elif isinstance(raw_insider_context, dict):
        payload_dict = raw_insider_context
    else:
        payload_dict = (
            raw_insider_context.model_dump()
            if hasattr(raw_insider_context, "model_dump")
            else dict(raw_insider_context)
        )

    validated_payload = InsiderContextPayload.model_validate(payload_dict)

    # 5. Assertions against structural payload
    if not mock_bq_data:
        # Ticker identification is expected, but all signal arrays must remain empty
        assert len(validated_payload.form4_signals) == 0, "Zero activity scenario must produce empty form4_signals."
        assert len(validated_payload.lobbying_signals) == 0, "Zero activity scenario must produce empty lobbying_signals."
        assert len(validated_payload.asymmetric_flags) == 0, "Zero activity scenario must produce empty asymmetric_flags."
    else:
        assert len(validated_payload.form4_signals) > 0, "Expected form4_signals to be populated."

    # 6. DeepEval Evaluation
    retrieval_context_payload = tool_outputs if tool_outputs else [json.dumps(mock_bq_data)]
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