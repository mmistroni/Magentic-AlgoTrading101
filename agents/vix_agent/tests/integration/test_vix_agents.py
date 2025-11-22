import pytest
import os
import shutil
from google.genai import types
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent
from vix_agent.models import DataPointerModel, SignalDataModel, FeatureDataModel
from vix_agent.vix_agents import FEATURE_AGENT, INGESTION_AGENT, SIGNAL_AGENT
from google.adk.sessions import InMemorySessionService, Session
from google.adk.runners import Runner

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
    Fixture to create and return the ADK Runner with the required app_name.
    """
    root_agent = SequentialAgent(
        name="COTAnalysisWorkflow",
        sub_agents=[INGESTION_AGENT, FEATURE_AGENT, SIGNAL_AGENT]
    )
    
    session_service = InMemorySessionService()
    
    # --- FIX APPLIED HERE ---
    runner = Runner(
        agent=root_agent,
        session_service=session_service,
        # The required keyword argument is now provided
        app_name="COTAnalysisTradingApp" 
    )
    # ------------------------
    
    return runner



def test_pipeline_data_flow_and_pydantic_output(cot_workflow_runner):
    """
    Tests sequential execution using the ADK Runner, verifying context state and Pydantic output.
    """
    """
    Tests sequential execution using the ADK Runner, verifying context state and Pydantic output.
    """
    test_prompt = "Start the trading signal generation workflow for Gold Futures now."
    session_id = "test_session_123"
    user_id = "test_user"
    app_name = "COTAnalysisTradingApp" # Define app_name here for reuse
    
    # 1. CREATE AND INITIALIZE THE SESSION with the initial state
    cot_workflow_runner.session_service.create_session(
        app_name=app_name, 
        session_id=session_id,
        user_id=user_id, 
        state={'market': 'Gold Futures'} 
    )
    
    # 2. ACT: Run the agent pipeline
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events = list(cot_workflow_runner.run(
        user_id=user_id, 
        session_id=session_id,
        new_message=user_content 
    ))

    # --- FINAL STATE RETRIEVAL FIX ---
    # Retrieve the full Session object using get_session()
    final_session = cot_workflow_runner.session_service.get_session(
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    
    # Access the state dictionary from the Session object
    final_state = final_session.state
    # ---------------------------------
    
    print("\n\n--- Running Pipeline Integration Test ---")

    # 1. ASSERT: Context Passing (URI Pointers)
    raw_pointer = final_state.get('raw_data_pointer')

    feature_pointer = final_state.get('feature_data_pointer')
    
    assert isinstance(raw_pointer, DataPointerModel)
    assert raw_pointer.uri == "./temp_data/raw_data_test.csv"
    print(f"✅ Context Check 1: Raw data URI passed successfully.")

    assert isinstance(feature_pointer, DataPointerModel)
    assert feature_pointer.uri == "./temp_data/engineered_data.csv"
    print(f"✅ Context Check 2: Feature data URI passed successfully.")

    # 2. ASSERT: Final Pydantic Output
    # The final output is usually the result of the last event, or stored under a known key
    final_result = final_state.get('final_output')

    assert isinstance(final_result, SignalDataModel)
    assert final_result.signal == "Buy"
    print(f"✅ Output Check 3: Final signal is correct ({final_result.signal}) and Pydantic validated.")
    print(f"   Reason: {final_result.reason}")

# To run this test:
# 1. Save the entire code block as 'test_pipeline_pytest.py'.
# 2. Run the command: 'pytest test_pipeline_pytest.py'