import pytest
import os
import shutil
from unittest import mock
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from vix_agent.models import DataPointerModel, SignalDataModel
# 💥 SIMPLIFIED IMPORTS: Only need the final pipeline
from vix_agent.vix_agents import COT_WORKFLOW_PIPELINE 
# We need to import the functions that the agents call for the mock setup to work
from vix_agent.tools import mock_ingestion_tool # We'll use this function to set up the raw file for the test

# -----------------------------------------------------------------------------

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
    Fixture to create and return the ADK Runner using the *original* imported pipeline.
    """
    session_service = InMemorySessionService()

    # 💥 SIMPLIFICATION: Use the pre-configured pipeline directly
    test_pipeline = COT_WORKFLOW_PIPELINE
    
    runner = Runner(
        agent=test_pipeline, 
        session_service=session_service,
        app_name="COTAnalysisTradingApp" 
    )
    
    return runner, session_service


# We will NOT patch the tools, but let the runner call the real tool logic.
# The tool logic will rely on the files being present.
@pytest.mark.asyncio
async def test_pipeline_data_flow_and_pydantic_output(cot_workflow_runner):
    """
    Tests sequential execution by letting the real tool logic run, 
    but controlling the input/output through file setup.
    """
    runner, session_service = cot_workflow_runner 
    session_id = "test_session_123"
    user_id = "test_user"
    app_name = "COTAnalysisTradingApp"
    test_prompt = "Start the trading signal generation workflow for Gold Futures now."

    # --- 1. SET UP MOCK FILE I/O ---

    # 1.1 INGESTION STEP: We will call the MOCK tool function manually 
    # to create the raw input file, as the real tool doesn't do I/O in your code.
    # The agent is configured to call `vix_data_tool`, which should return the URI.
    # We must manually ensure the raw data file is created at the expected URI.
    
    expected_raw_uri = mock_ingestion_tool() # Executes the mock to create the raw file
    
    # 1.2 FEATURE STEP MOCK: The feature tool reads this, processes, and writes the engineered file.
    # We let the feature_engineering_tool run its full logic in a sub-agent.
    # The output will be the engineered URI.
    expected_engineered_uri = './temp_data/engineered_data.csv'
    
    # 1.3 SIGNAL STEP MOCK: The signal tool reads the engineered file 
    # and calculates the signal.
    
    # We need to *know* what signal the mock data will generate.
    # The mock data creates an engineered CSV with Z-Score 0.5 + 3*0.1 = 0.8
    # and VIX Percentile 95 - 3*5 = 80.
    # The trading logic is:
    # if cot_z < -1.5 and vix_p > 90.0: "Buy"
    # elif cot_z > 1.5 and vix_p < 10.0: "Sell"
    # else: "Neutral"
    
    # Based on the data the mock_ingestion_tool creates, the signal should be NEUTRAL.
    expected_signal = "Neutral"
    expected_reason = "Metrics are within normal bounds. COT Z-Score: 0.80, VIX Percentile: 80.00."


    # 2. CREATE AND INITIALIZE THE SESSION
    await session_service.create_session(
        app_name=app_name, 
        session_id=session_id,
        user_id=user_id, 
        state={'market': 'Gold Futures'} 
    )
    
    # 3. ACT: Run the agent pipeline
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events_generator = runner.run_async( 
        user_id=user_id, 
        session_id=session_id,
        new_message=user_content 
    )
    
    final_events = [event async for event in final_events_generator]

    # Retrieve the final session state
    final_session = await session_service.get_session( 
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    final_state = final_session.state
    
    print("\n\n--- Running Pipeline Integration Test (Simplest Setup) ---")

    # =========================================================================
    # 4. ASSERT: Context Passing & Pydantic Validation
    # =========================================================================

    # --- INGESTION Check ---
    raw_pointer_data = final_state.get('raw_data_pointer')
    raw_pointer = DataPointerModel(**raw_pointer_data)
    assert raw_pointer.uri == expected_raw_uri
    print(f"✅ Stage 1: Raw data URI Pydantic object validated.")

    # --- FEATURE Check ---
    feature_pointer_data = final_state.get('feature_data_pointer')
    feature_pointer = DataPointerModel(**feature_pointer_data)
    assert feature_pointer.uri == expected_engineered_uri
    print(f"✅ Stage 2: Feature data URI Pydantic object validated.")


    # --- FINAL SIGNAL Check ---
    final_result_data = final_state.get('final_output')
    final_result = SignalDataModel(**final_result_data)

    assert isinstance(final_result, SignalDataModel)
    assert final_result.signal == expected_signal
    assert final_result.reason.startswith(expected_reason[:30]) # Check start of reason for float variance
    
    print(f"✅ Stage 3: Final signal is correct ({final_result.signal}) and Pydantic validated.")