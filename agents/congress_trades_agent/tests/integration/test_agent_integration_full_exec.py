import os
from pathlib import Path
import pytest

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
    name="CongressTrader Full Integration Decision Synthesis Metric",
    criteria="""
1. VALID TRADE ACTION: Verify that the agent outputs a clear structural decision containing an action (BUY, SELL, HOLD), a conviction score, and a valuation verdict.
2. DATA GROUNDING: Ensure that the rationale relies on real retrieved congressional, insider, and historical episodic data.
3. STRUCTURE & PERSISTENCE: Check that the synthesis addresses fundamental health and historical trailing performance coherently.
""",
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=TRUSTWORTHY_SCORE_THRESHOLD,
    model=gemini_evaluator,
)

@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing credentials for full live BigQuery execution",
)
async def test_agent_integration_full_exec():
    """Executes CongressTrader agent completely unmocked against live BigQuery storage,
    fetching real historical episodes, calculating real trailing returns, and persisting records.
    """
    user_id = "trader_full_integration_user"

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

    # Let the agent autonomously scan and select its target ticker and execute the full loop
    trader_prompt = (
        "Perform a fully unmocked live trade evaluation. Scan recent congressional disclosures and "
        "insider trading data from BigQuery, fetch historical past episodes from storage, compute trailing returns, "
        "adapt your conviction weights empirically, synthesize a final decision record, and store it back to BigQuery."
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

    print("\n================ [FULL LIVE EXECUTION] CONGRESS TRADER OUTPUT ================")
    print(trader_text)

    # --- MOVED UP: Inspect tool discoveries and outputs before assertions ---
    print("\n================ [DISCOVERY & TOOL OUTPUTS INSPECTION] ================")
    if tool_outputs:
        for idx, output in enumerate(tool_outputs, 1):
            print(f"Tool Output #{idx}:\n{output}\n{'-'*50}")
    else:
        print("No tool outputs were captured during execution.")

    assert len(trader_text) > 20, "CongressTrader full execution output was too brief."

    test_case = LLMTestCase(
        input=trader_prompt,
        actual_output=trader_text,
        retrieval_context=tool_outputs if tool_outputs else ["Live unmocked BigQuery database interaction payload"],
    )

    trader_evaluation_metric.measure(test_case)

    print(f"\n[GEval Full Integration Score]: {trader_evaluation_metric.score}")
    print(f"[GEval Reason]: {trader_evaluation_metric.reason}")

    assert trader_evaluation_metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, (
        f"CongressTrader unmocked integration test failed evaluation "
        f"with score {trader_evaluation_metric.score}.\nReason: {trader_evaluation_metric.reason}"
    )