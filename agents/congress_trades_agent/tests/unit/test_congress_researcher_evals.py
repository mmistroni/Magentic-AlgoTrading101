import json
import pytest
from typing import Optional, Type
from pydantic import BaseModel
from unittest.mock import patch

from deepeval import assert_test
from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.models import DeepEvalBaseLLM

from google.genai import Client, types
from google.adk.runners import InMemoryRunner
from congress_trades_agent.skills.congress_researcher.agent import congress_researcher


# --- Custom Gemini Model Wrapper for DeepEval ---
class GeminiJudge(DeepEvalBaseLLM):
    def __init__(self, model_name: str = "gemini-2.5-flash"):
        self.model_name = model_name
        self.client = Client()

    def load_model(self):
        return self.client

    def get_model_name(self) -> str:
        return self.model_name

    def generate(self, prompt: str) -> str:
        response = self.client.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return response.text

    async def a_generate(self, prompt: str) -> str:
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
        )
        return response.text

    async def a_generate_with_schema(
        self, prompt: str, schema: Type[BaseModel]
    ) -> tuple[BaseModel, float]:
        response = await self.client.aio.models.generate_content(
            model=self.model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=schema,
            ),
        )
        # Parse output into the expected Pydantic schema
        parsed_data = schema.model_validate_json(response.text)
        return parsed_data, 0.0  # Returns (data, cost)


# Instantiate the custom evaluator
gemini_evaluator = GeminiJudge()

political_relevance_metric = GEval(
    name="Political Strategy Relevance",
    criteria="""
    1. Verify high-conviction ticker accumulation is clearly identified.
    2. Ensure market regime (uptrend vs. downtrend) is highlighted.
    3. Verify tone is structured as a Washington Policy Strategist.
    """,
    evaluation_params=[SingleTurnParams.INPUT, SingleTurnParams.ACTUAL_OUTPUT],
    threshold=0.7,
    model=gemini_evaluator,
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

    prompt_text = "Summarize congressional trading activity and political context for 2026-07-01."
    user_id = "test_user"
    session_id = "test_session"

    runner = InMemoryRunner(agent=congress_researcher)

    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id
    )

    user_message = types.Content(
        role="user",
        parts=[types.Part.from_text(text=prompt_text)]
    )

    output_text = ""
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=user_message
    ):
        if hasattr(event, "content") and event.content:
            output_text += str(event.content)
        elif hasattr(event, "text") and event.text:
            output_text += str(event.text)

    test_case = LLMTestCase(
        input=prompt_text,
        actual_output=output_text,
    )

    assert_test(test_case, [political_relevance_metric])

    