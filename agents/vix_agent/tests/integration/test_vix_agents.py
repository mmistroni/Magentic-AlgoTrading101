import pytest
import os
import shutil
from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.agents import LlmAgent, SequentialAgent
from google.adk.runners import Runner
from vix_agent.models import DataPointerModel, SignalDataModel, FeatureDataModel
from google.adk.tools import FunctionTool
# Assuming the necessary imports from vix_agent.vix_agents and vix_agent.agent
from vix_agent.vix_agents import (
    INGESTION_TOOL_CALLER,
    INGESTION_MODEL_GENERATOR,
    FEATURE_TOOL_CALLER,
    FEATURE_MODEL_GENERATOR,
    SIGNAL_TOOL_CALLER,
    SIGNAL_MODEL_GENERATOR,
)
from vix_agent.agent import COT_WORKFLOW_PIPELINE
from vix_agent.tools import mock_feature_engineering_tool, mock_ingestion_tool, mock_signal_generation_tool

# --- DEPENDENCY INJECTION MOCK TOOLS DICTIONARY ---
# This dictionary is passed to the Runner to satisfy all tool calls made by the agents.
TEST_TOOLS = {
    # The keys must match the function name the LLM is instructed to call in the agents.
    "mock_ingestion_tool": mock_ingestion_tool,
    "mock_feature_engineering_tool": mock_feature_engineering_tool,
    "mock_signal_generation_tool": mock_signal_generation_tool,
}
# ----------------------------------------------------

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
    Final Fix: CLONE *ALL* sub-agents (tool-callers and model-generators) 
    to prevent the 'already has a parent' error.
    """
    session_service = InMemorySessionService()

    # 1. Create the FunctionTool objects needed for injection
    from google.adk.tools import FunctionTool
    ingestion_tool = FunctionTool(mock_ingestion_tool)
    feature_tool = FunctionTool(mock_feature_engineering_tool)
    signal_tool = FunctionTool(mock_signal_generation_tool)
    
    # 2. CLONE *ALL* six sub-agents and apply tool injection where necessary
    
    # --- Tool Callers (Inject Tool) ---
    ingestion_tool_caller_test = INGESTION_TOOL_CALLER.clone(
        update={'tools': [ingestion_tool]}
    )
    feature_tool_caller_test = FEATURE_TOOL_CALLER.clone(
        update={'tools': [feature_tool]}
    )
    signal_tool_caller_test = SIGNAL_TOOL_CALLER.clone(
        update={'tools': [signal_tool]}
    )
    
    # --- Model Generators (Just Clone) ---
    ingestion_model_generator_test = INGESTION_MODEL_GENERATOR.clone()
    feature_model_generator_test = FEATURE_MODEL_GENERATOR.clone()
    signal_model_generator_test = SIGNAL_MODEL_GENERATOR.clone()

    # 3. Assemble the new test-specific pipeline using ONLY the cloned instances.
    test_pipeline = SequentialAgent(
        name=COT_WORKFLOW_PIPELINE.name, 
        sub_agents=[
            ingestion_tool_caller_test,
            ingestion_model_generator_test,
            feature_tool_caller_test,
            feature_model_generator_test,
            signal_tool_caller_test,
            signal_model_generator_test
        ]
    )
    
    runner = Runner(
        agent=test_pipeline, 
        session_service=session_service,
        app_name="COTAnalysisTradingApp" 
    )
    
    return runner, session_service


@pytest.mark.asyncio
async def test_pipeline_data_flow_and_pydantic_output(cot_workflow_runner):
    """
    Tests sequential execution using the ADK Runner, verifying context state 
    at every stage and the final Pydantic output.
    """
    runner, session_service = cot_workflow_runner 
    
    test_prompt = "Start the trading signal generation workflow for Gold Futures now."
    session_id = "test_session_123"
    user_id = "test_user"
    app_name = "COTAnalysisTradingApp"
    
    # 1. CREATE AND INITIALIZE THE SESSION
    await session_service.create_session(
        app_name=app_name, 
        session_id=session_id,
        user_id=user_id, 
        state={'market': 'Gold Futures'} 
    )
    
    # 2. ACT: Run the agent pipeline
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events_generator = runner.run_async( 
        user_id=user_id, 
        session_id=session_id,
        new_message=user_content 
    )
    
    # Consume the async generator to ensure the pipeline runs to completion
    final_events = [event async for event in final_events_generator]

    # Retrieve the final session state
    final_session = await session_service.get_session( 
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    final_state = final_session.state
    
    print("\n\n--- Running Pipeline Integration Test ---")

    # =========================================================================
    # 1. ASSERT: Context Passing - RAW STRING OUTPUTS (Validates Tool Caller Agents)
    # =========================================================================
    
    # Check key created by INGESTION_TOOL_CALLER
    assert 'ingestion_raw_output' in final_state
    expected_raw_uri = './temp_data/raw_data_test.csv'
    assert final_state['ingestion_raw_output'] == expected_raw_uri
    print(f"✅ Context Check 1: Raw ingestion URI string saved correctly: {expected_raw_uri}")

    # Check key created by FEATURE_TOOL_CALLER
    assert 'feature_tool_raw_output' in final_state
    expected_engineered_uri = './temp_data/engineered_data.csv'
    assert final_state['feature_tool_raw_output'] == expected_engineered_uri
    print(f"✅ Context Check 2: Raw feature URI string saved correctly: {expected_engineered_uri}")

    # Check key created by SIGNAL_TOOL_CALLER (Raw JSON output from the mock tool)
    assert 'raw_signal_json' in final_state
    expected_signal_json = '{"signal": "Buy", "reason": "Mocked: High COT Z-Score indicates strong bullish conviction."}'
    assert final_state['raw_signal_json'] == expected_signal_json
    print(f"✅ Context Check 3: Raw signal JSON string saved correctly.")


    # =========================================================================
    # 2. ASSERT: Pydantic Data Pointers (Validates Model Generator Agents)
    # =========================================================================

    # --- Validate INGESTION_MODEL_GENERATOR Output ---
    raw_pointer_data = final_state.get('raw_data_pointer')
    raw_pointer = DataPointerModel(**raw_pointer_data)
    
    assert isinstance(raw_pointer, DataPointerModel)
    assert raw_pointer.uri == expected_raw_uri
    print(f"✅ Context Check 4: Raw data URI Pydantic object validated.")

    # --- Validate FEATURE_MODEL_GENERATOR Output ---
    feature_pointer_data = final_state.get('feature_data_pointer')
    feature_pointer = DataPointerModel(**feature_pointer_data)

    assert isinstance(feature_pointer, DataPointerModel)
    assert feature_pointer.uri == expected_engineered_uri
    print(f"✅ Context Check 5: Feature data URI Pydantic object validated.")

    # =========================================================================
    # 3. ASSERT: Final Pydantic Output (Validates SIGNAL_MODEL_GENERATOR)
    # =========================================================================
    
    final_result_data = final_state.get('final_output')
    final_result = SignalDataModel(**final_result_data)

    assert isinstance(final_result, SignalDataModel)
    assert final_result.signal == "Buy"
    # Verify the reason matches the data provided by the mock
    assert final_result.reason == "Mocked: High COT Z-Score indicates strong bullish conviction."
    
    print(f"✅ Output Check 6: Final signal is correct ({final_result.signal}) and Pydantic validated.")
    print(f"   Reason: {final_result.reason}")

# End of Test File