import pytest
import os
import shutil
from google.genai import types
# You might need to import Session if it's not in google.adk.sessions
from google.adk.sessions import InMemorySessionService, Session 
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from vix_agent.models import DataPointerModel, SignalDataModel, FeatureDataModel

# --- AMENDMENT 1: USE THE CORRECT PIPELINE IMPORTS ---
# We assume the new 6-agent pipeline structure is defined under COT_WORKFLOW_PIPELINE
# in vix_agent.vix_agents.
from vix_agent.vix_agents import (
    INGESTION_TOOL_CALLER,
    INGESTION_MODEL_GENERATOR,
    FEATURE_TOOL_CALLER,
    FEATURE_MODEL_GENERATOR,
    SIGNAL_AGENT
)
from vix_agent.agent import COT_WORKFLOW_PIPELINE
# We can remove the old imports here since the pipeline object is used.

from google.adk.runners import Runner

# --------------------------------------------------------------------------
# --- AMENDMENT 2: DEFINE MOCK TOOLS NEEDED BY THE NEW FEATURE_TOOL_CALLER ---
# Assuming mock_ingestion_tool is defined elsewhere or in vix_agent.tools
# We must define the mock tool needed by the FeatureToolCaller.

# --------------------------------------------------------------------------

@pytest.fixture(scope="module")
def cleanup_temp_data():
    """Fixture to ensure the temp_data directory is cleaned before and after tests."""
    temp_dir = "./temp_data"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    yield
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@pytest.fixture
def cot_workflow_runner(cleanup_temp_data):
    """
    Fixture to create and return the ADK Runner AND the SessionService.
    Uses the final 6-agent pipeline object.
    """
    # --- AMENDMENT 3: USE THE CORRECT SequentialAgent OBJECT ---
    # The fixture must use the pre-defined COT_WORKFLOW_PIPELINE object.
    # The old sub_agents=[INGESTION_AGENT, ...] is incorrect here.
    root_agent = COT_WORKFLOW_PIPELINE
    # -----------------------------------------------------------
    
    session_service = InMemorySessionService()
    
    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        app_name="COTAnalysisTradingApp" 
    )
    
    # This unpack fix is now correct:
    return runner, session_service

@pytest.mark.asyncio
async def test_pipeline_data_flow_and_pydantic_output(cot_workflow_runner):
    """
    Tests sequential execution using the ADK Runner, verifying context state and Pydantic output.
    """
    # This unpack fix is now correct:
    runner, session_service = cot_workflow_runner 
    
    test_prompt = "Start the trading signal generation workflow for Gold Futures now."
    session_id = "test_session_123"
    user_id = "test_user"
    app_name = "COTAnalysisTradingApp"
    
    # 1. CREATE AND INITIALIZE THE SESSION with the initial state (AWAITED)
    await session_service.create_session(
        app_name=app_name, 
        session_id=session_id,
        user_id=user_id, 
        state={'market': 'Gold Futures'} 
    )
    
    # 2. ACT: Run the agent pipeline (ASYNC GENERATOR)
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    
    final_events_generator = runner.run_async( 
        user_id=user_id, 
        session_id=session_id,
        new_message=user_content 
    )
    
    # Consume the async generator
    final_events = [event async for event in final_events_generator]


    # --- FINAL STATE RETRIEVAL FIX (AWAITED) ---
    final_session = await session_service.get_session( 
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    
    final_state = final_session.state
    # ---------------------------------
    
    print("\n\n--- Running Pipeline Integration Test ---")

    # 1. ASSERT: Context Passing (URI Pointers)
    
    # Retrieve data as dictionaries
    raw_pointer_data = final_state.get('raw_data_pointer')
    feature_pointer_data = final_state.get('feature_data_pointer')
    
    # --- FIX 1: Manually cast dictionary to DataPointerModel ---
    raw_pointer = DataPointerModel(**raw_pointer_data)
    # -----------------------------------------------------------
    
    # The assertion now checks the cast object
    assert isinstance(raw_pointer, DataPointerModel)
    assert raw_pointer.uri == "./temp_data/raw_data_test.csv"
    print(f"✅ Context Check 1: Raw data URI passed successfully.")

    # --- FIX 2: Manually cast dictionary to DataPointerModel ---
    feature_pointer = DataPointerModel(**feature_pointer_data)
    # -----------------------------------------------------------

    assert isinstance(feature_pointer, DataPointerModel)
    assert feature_pointer.uri == "./temp_data/engineered_data.csv"
    print(f"✅ Context Check 2: Feature data URI passed successfully.")

    # 2. ASSERT: Final Pydantic Output
    final_result_data = final_state.get('final_output')

    # --- FIX 3: Manually cast dictionary to SignalDataModel ---
    final_result = SignalDataModel(**final_result_data)
    # -----------------------------------------------------------

    # This check relies on the SIGNAL_AGENT working
    assert isinstance(final_result, SignalDataModel)
    assert final_result.signal == "Buy"
    print(f"✅ Output Check 3: Final signal is correct ({final_result.signal}) and Pydantic validated.")
    print(f"   Reason: {final_result.justification}")
    # To run this test:
    # 1. Save the entire code block as 'test_pipeline_pytest.py'.
    # 2. Run the command: 'pytest test_pipeline_pytest.py'