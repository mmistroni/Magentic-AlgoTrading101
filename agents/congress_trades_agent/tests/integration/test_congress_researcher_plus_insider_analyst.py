import json
import os
from pathlib import Path
import pytest

from google.adk.runners import Runner
from google.adk.sessions import InMemorySessionService
from google.genai import types

from deepeval.metrics import GEval
from deepeval.test_case import LLMTestCase, SingleTurnParams
from deepeval.models import GeminiModel

from congress_trades_agent.skills.congress_researcher.agent import congress_researcher
from congress_trades_agent.skills.insider_analyst.agent import insider_analyst

GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

APP_NAME = "congress_trades_agent"
TRUSTWORTHY_SCORE_THRESHOLD = 0.85

# Initialize evaluation model
gemini_evaluator = GeminiModel(
    model="gemini-2.5-flash",
    api_key=os.getenv("GEMINI_API_KEY"),
)

# Integration anti-hallucination and cross-agent confluence metric
live_confluence_evaluation_metric = GEval(
    name="Live Multi-Agent Confluence & Non-Hallucination Metric",
    criteria="""
1. STRICT TRUTHFULNESS: Verify that summaries derived from live BigQuery data accurately reflect actual congressional, insider, or contract signals without fabricating transactions, dollar volumes, or entities.
2. CROSS-AGENT CONSISTENCY: Ensure that the insights produced by the second agent (InsiderAnalyst) align logically with the context established by the first agent (CongressResearcher) for the target ticker.
3. NO PHANTOM ENTITIES: Do not invent tickers, executives, or disclosures outside the retrieved session context.
""",
    evaluation_params=[
        SingleTurnParams.INPUT,
        SingleTurnParams.ACTUAL_OUTPUT,
        SingleTurnParams.RETRIEVAL_CONTEXT,
    ],
    threshold=TRUSTWORTHY_SCORE_THRESHOLD,
    model=gemini_evaluator,
)

MULTI_AGENT_SCENARIOS = [
    ("tsm_congress_and_insider", "TSM", "2026-10-07"),
    ("cdns_triple_confluence", "CDNS", "2026-10-01"),
    ("ibm_congress_and_contracts", "IBM", "2026-10-06"),
]


@pytest.mark.asyncio
@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing credentials for live BigQuery execution",
)
@pytest.mark.parametrize("scenario_name, ticker, analysis_date", MULTI_AGENT_SCENARIOS)
async def test_dual_agent_live_execution_with_evaluation(scenario_name, ticker, analysis_date):
    """Executes CongressResearcher and InsiderAnalyst sequentially on live BigQuery data,
    prints responses, and evaluates output against hallucinations using GEval.
    """
    user_id = f"live_eval_user_{scenario_name}"

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

    # --- STEP 1: Execute CongressResearcher ---
    congress_runner = Runner(
        agent=congress_researcher, 
        app_name=APP_NAME, 
        session_service=shared_session_service
    )

    congress_prompt = (
        f"Analyze Congressional disclosures and federal contracts for ticker {ticker} "
        f"as of analysis date {analysis_date}."
    )
    user_msg_1 = types.Content(role="user", parts=[types.Part(text=congress_prompt)])

    congress_text = ""
    tool_outputs = []

    async for event in congress_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg_1,
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_response") and part.function_response:
                    tool_outputs.append(str(part.function_response.response))
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                congress_text = "".join(part.text for part in event.content.parts if part.text)

    print(f"\n================ [{scenario_name.upper()}] CONGRESS RESEARCHER OUTPUT ================")
    print(congress_text)

    assert len(congress_text) > 20, f"CongressResearcher commentary for {ticker} was too brief."

    # --- STEP 2: Execute InsiderAnalyst ---
    insider_runner = Runner(
        agent=insider_analyst,
        app_name=APP_NAME,
        session_service=shared_session_service,
    )

    insider_prompt = (
        f"Analyze Form 4 corporate insider trading and lobbying spend for ticker {ticker} "
        f"as of analysis date {analysis_date}."
    )
    user_msg_2 = types.Content(role="user", parts=[types.Part(text=insider_prompt)])

    insider_text = ""
    async for event in insider_runner.run_async(
        user_id=user_id,
        session_id=session.id,
        new_message=user_msg_2,
    ):
        if hasattr(event, "content") and event.content and event.content.parts:
            for part in event.content.parts:
                if hasattr(part, "function_response") and part.function_response:
                    tool_outputs.append(str(part.function_response.response))
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                insider_text = "".join(part.text for part in event.content.parts if part.text)

    print(f"\n================ [{scenario_name.upper()}] INSIDER ANALYST OUTPUT ================")
    print(insider_text)

    assert len(insider_text) > 20, f"InsiderAnalyst commentary for {ticker} was too brief."

    # --- STEP 3: Inspect Session State & Run GEval Hallucination Check ---
    updated_session = await shared_session_service.get_session(
        app_name=APP_NAME, user_id=user_id, session_id=session.id
    )

    combined_output = f"Congress Analysis:\n{congress_text}\n\nInsider/Lobbying Analysis:\n{insider_text}"

    test_case = LLMTestCase(
        input=f"Multi-agent live analysis for {ticker} on {analysis_date}",
        actual_output=combined_output,
        retrieval_context=tool_outputs if tool_outputs else ["Live BigQuery execution payload"],
    )

    live_confluence_evaluation_metric.measure(test_case)

    print(f"\n[GEval Score for {scenario_name}]: {live_confluence_evaluation_metric.score}")
    print(f"[GEval Reason]: {live_confluence_evaluation_metric.reason}")

    assert live_confluence_evaluation_metric.score >= TRUSTWORTHY_SCORE_THRESHOLD, (
        f"Live multi-agent execution for {scenario_name} failed hallucination evaluation "
        f"with score {live_confluence_evaluation_metric.score}.\nReason: {live_confluence_evaluation_metric.reason}"
    )


    