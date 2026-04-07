import pytest
import json
import os
import shutil

from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner

# 1. Import your actual pipeline
# (Update 'your_module' to your actual project structure)
from congress_trades_agent.congress_agents import CONGRESS_PIPELINE

# 2. IMPORT YOUR MOCK TOOLS DIRECTLY FROM YOUR FILE
from mock_tools import (
    fetch_political_signals_tool as mock_fetch_political,
    fetch_form4_signals_tool as mock_fetch_form4,
    check_fundamentals_tool as mock_check_fundamentals
)

# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture(scope="module")
def cleanup_temp_data():
    temp_dir = "./temp_data"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    yield
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@pytest.fixture
def alpha_workflow_runner(cleanup_temp_data):
    """Initializes the ADK Runner with our pipeline."""
    session_service = InMemorySessionService()
    runner = Runner(
        agent=CONGRESS_PIPELINE, 
        session_service=session_service,
        app_name="AlphaTradingApp" 
    )
    return runner, session_service

# =============================================================================
# THE INTEGRATION TEST
# =============================================================================

@pytest.mark.asyncio
async def test_alpha_pipeline_logic_and_guardrails(mocker, alpha_workflow_runner):
    runner, session_service = alpha_workflow_runner 

    # --- PATCH THE REAL TOOLS WITH YOUR IMPORTED MOCKS ---
    # This tells pytest: "When the agent tries to call the real tool, 
    # run the mock tool we imported from mock_tools.py instead!"
    mocker.patch('your_module.tools.fetch_political_signals_tool', side_effect=mock_fetch_political)
    mocker.patch('your_module.tools.fetch_form4_signals_tool', side_effect=mock_fetch_form4)
    mocker.patch('your_module.tools.check_fundamentals_tool', side_effect=mock_check_fundamentals)

    session_id = "test_session_alpha_003"
    user_id = "test_quant"
    app_name = "AlphaTradingApp"
    
    test_prompt = "Run the Alpha strategy for 2024-10-15."

    await session_service.create_session(
        app_name=app_name, 
        session_id=session_id,
        user_id=user_id, 
        state={} 
    )
    
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events_generator = runner.run_async( 
        user_id=user_id, 
        session_id=session_id,
        new_message=user_content 
    )
    
    print("\n" + "="*70)
    print("🕵️ TRACE: Pipeline Execution & Reasoning")
    print("="*70)

    async for event in final_events_generator:
        if hasattr(event, 'agent_call'):
            print(f"\n🚀 [AGENT HANDOFF]: {event.agent_call.agent_name}")
            
        if hasattr(event, 'tool_call'):
            print(f"🛠️ [TOOL CALLED]: {event.tool_call.function_name}({event.tool_call.arguments})")

        if hasattr(event, 'model_response') and event.model_response:
            thought = event.model_response.text.strip()
            if thought:
                print(f"🧠 [THOUGHT/OUTPUT]: {thought[:200]}...\n")

    print("="*70)

    # --- FINAL ASSERTIONS ---
    final_session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    final_state = final_session.state
    
    final_plan_str = final_state.get('final_trade_plan')
    assert final_plan_str is not None, "Trader failed to output a final plan!"
    
    # Extract JSON safely
    clean_json_str = final_plan_str.replace("```json", "").replace("```", "").strip()
    trade_plan = json.loads(clean_json_str)

    actions = {trade["ticker"]: trade["action"] for trade in trade_plan}
    
    # 🎯 Verify against your specific mock_tools.py logic
    assert "BUY" in actions["BE"], "Agent failed to buy the Golden Confluence stock (BE)!"
    assert actions["MOH"] == "PASS", "Agent mistakenly bought a FALLING KNIFE (MOH)!"
    assert actions["EQIX"] == "PASS", "Agent ignored the Safety Rails and bought EQIX!"

    print("✅ All Agent Logic and Guardrails passed successfully!")