import pytest
from unittest.mock import patch
from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams

from congress_trades_agent.skills.congress_researcher.agent import congress_researcher

# Define Evaluation Rubric
political_relevance_metric = GEval(
    name="Political Strategy Relevance",
    criteria="""
    1. Verify high-conviction ticker accumulation is clearly identified.
    2. Ensure market regime (uptrend vs. downtrend) is highlighted.
    3. Verify tone is structured as a Washington Policy Strategist.
    """,
    evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
    threshold=0.7,
)

@pytest.mark.asyncio
@patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_data")
async def test_eval_high_conviction_response(mock_get_bq_data):
    """Evaluates CongressResearcher response quality under high-conviction buying."""
    mock_get_bq_data.return_value = [
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
    ]

    prompt = "Summarize congressional trading activity and political context for 2026-07-01."
    
    # Iterate over Google ADK async event stream to collect response text
    output_text = ""
    async for event in congress_researcher.run_async(prompt):
        if hasattr(event, "content") and event.content:
            output_text += event.content
        elif hasattr(event, "text") and event.text:
            output_text += event.text

    test_case = LLMTestCase(
        input=prompt,
        actual_output=output_text,
    )

    assert_test(test_case, [political_relevance_metric])