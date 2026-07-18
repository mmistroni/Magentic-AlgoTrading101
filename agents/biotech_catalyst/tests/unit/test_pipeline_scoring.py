import pytest
from google.adk.agents import LlmAgent
from google.adk.sessions import InMemorySessionService
from google.adk.eval.models import AgentRunOutput
# Correct ADK evaluation framework paths
from google.adk.evaluation import ResponseEvaluator, TrajectoryEvaluator

#
# ==========================================
# 1. SETUP: Instantiate Agent & Session Service
# ==========================================
# 1. Create an isolated, in-memory storage layer for your test runtime
session_service = InMemorySessionService()

# 2. Instantiate your short selling agent
short_selling_agent = LlmAgent(
    name="short_selling_analyst",
    model="gemini-2.5-flash",
    instruction="You are a financial analyst. Give a concise risk verdict (BEARISH/NEUTRAL) and note key technical breakdowns.",
)

# ==========================================
# 2. THE SCORING UNIT TEST
# ==========================================
def test_agent_response_scoring_in_memory():
    """Executes the agent and programmatically scores its output using InMemorySessionService."""
    
    user_input = "Analyze XYZ Corp. It just crossed below its 200-day moving average on massive volume."
    expected_response = "Verdict: BEARISH. The stock broke below its 200-day moving average on high volume."
    
    # 3. Use the service to create/initialize the conversation container programmatically
    session = session_service.create_session(
        session_id="eval_session_001",
        app_name="short_selling_app"
    )
    
    # 4. Process the prompt inside the created session state context
    # Note: Depending on the specific ADK release version, execution is passed through 
    # either session.send_message(user_input, agent=short_selling_agent) 
    # or the service router itself.
    response = session.send_message(user_input, agent=short_selling_agent)
    
    # 5. Extract evaluation parameters
    actual_output = AgentRunOutput(
        final_response=response.text,
        tool_trajectory=response.trajectory
    )
    
    # 6. Evaluate and assert your score thresholds
    response_evaluator = ResponseEvaluator()
    score_result = response_evaluator.evaluate(
        expected=expected_response,
        actual=actual_output.final_response
    )
    
    print(f"\n[EVAL RESULT] Dynamic Response Score: {score_result.score}")
    assert score_result.score >= 0.75, f"Response fell short of expectations! Got: {score_result.score}"