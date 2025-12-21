import pytest
import os
import shutil

from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from pytest import approx
from vix_agent.models import DataPointerModel, SignalDataModel
# 1. Import the main pipeline
from vix_agent.vix_agents import COT_WORKFLOW_PIPELINE 
# 2. Import the ingestion tool for manual file creation
from vix_agent.tools import ingestion_tool 
import pandas as pd

# -----------------------------------------------------------------------------
# --- FIXTURES ---
# -----------------------------------------------------------------------------

@pytest.fixture
def mock_vix_data():
    """Returns a mock DataFrame for the daily VIX price data."""
    raw_data = [
        ['date', 'open', 'high', 'low', 'close', 'volume'],
    ['2025-11-20', 16.670000076293945,17.559999465942383,15.239999771118164,15.239999771118164,1000],
    ['2025-11-21', 15.229999542236328,15.720000267028809,14.539999961853027,14.600000381469727,10000],
    ['2025-11-22', 14.949999809265137,15.029999732971191,13.880000114440918,14.100000381469727,10000]
    ]
    
    header = raw_data[0]
    data_rows = raw_data[1:]
    
    # 2. Create the initial DataFrame
    return pd.DataFrame(data_rows, columns=header)


@pytest.fixture
def mock_cot_data():
    """Returns a mock DataFrame for the weekly COT data, forcing an extreme rank."""
    raw_data = [
        ['Timestamp', 'Raw_COT_Value', 'Raw_VIX_Value'],
        ['2025-11-20', '10.5', '90.0'],
        ['2025-11-21', '11.2', '85.5'],
        ['2025-11-22', '12.0', '78.0']
    ]

    header = raw_data[0]
    data_rows = raw_data[1:]
    
    # 2. Create the initial DataFrame
    return pd.DataFrame(data_rows, columns=header)





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

    # Use the pre-configured pipeline directly 
    test_pipeline = COT_WORKFLOW_PIPELINE
    
    # Initialize the Runner
    runner = Runner(
        agent=test_pipeline, 
        session_service=session_service,
        app_name="COTAnalysisTradingApp" 
    )
    
    return runner, session_service

# -----------------------------------------------------------------------------
# --- THE INTEGRATION TEST ---
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_data_ingestion_and_pydantic_output(mocker, 
                                                           mock_vix_data, 
                                                           mock_cot_data,
                                                           cot_workflow_runner):
    """
    Tests the pipeline execution, verifying state passing and Pydantic validation 
    for the ingestion stage using the output_key mechanism.
    """
    runner, session_service = cot_workflow_runner 

    mocker.patch('vix_agent.tools._get_raw_data', return_value=mock_cot_data)
    mocker.patch('vix_agent.tools._get_vix_raw_data', return_value=mock_vix_data)



    session_id = "test_session_123"
    user_id = "test_user"
    app_name = "COTAnalysisTradingApp"
    test_prompt = "Start the trading signal generation workflow for Gold Futures now."

    # --- 1. SETUP EXPECTED DATA AND FILE I/O ---

    # Define the file path the tool will create and return.
    expected_raw_uri = "./temp_data/raw_data_test.csv"
    expected_vix_raw_uri = "./temp_data/vix_raw_data_test.csv"


    # Manually execute the ingestion tool to create the file on disk.
    # The tool's return value (the URI) is ignored in this manual call.
    ingestion_tool("Gold Futures") 
    
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
    
    # Consume the async generator
    final_events = [event async for event in final_events_generator]

    # Retrieve the final session state
    final_session = await session_service.get_session( 
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    final_state = final_session.state
    
    print("\n\n--- DEBUGGING: Ingestion Pipeline ---")

    # =========================================================================
    # 4. ASSERT: Tool Output Verification
    # =========================================================================

    # Check 1: Tool Caller Output. The URI is saved to 'ingestion_raw_output' via the agent's output_key.
    raw_uri_string_output = final_state.get('ingestion_raw_output')
    print(f"DEBUG 1: 'ingestion_raw_output' context key value (URI string): '{raw_uri_string_output}'")
    
    vix_uri_string_output = final_state.get('vix_raw_output_uri')
    print(f"DEBUG 1.5: 'vix_ingestion_raw_output' context key value (URI string): '{vix_uri_string_output}'")
    
    # This assertion verifies the LlmAgent successfully captured the tool's return value (the URI).
    assert raw_uri_string_output == expected_raw_uri
    assert vix_uri_string_output == expected_vix_raw_uri
    
    print("✅ CHECK 1: Ingestion Tool's URI output was successfully saved to context.")
    
    
    
@pytest.mark.asyncio
async def test_pipeline_data_feature_and_pydantic_output(mocker, 
                                                           mock_vix_data, 
                                                           mock_cot_data,
                                                           cot_workflow_runner):
    """
    Tests the pipeline execution, verifying state passing and Pydantic validation 
    for the ingestion stage using the output_key mechanism.
    """
    runner, session_service = cot_workflow_runner 
    session_id = "test_session_123"
    user_id = "test_user"
    app_name = "COTAnalysisTradingApp"
    test_prompt = "Start the trading signal generation workflow for Gold Futures now."

    mocker.patch('vix_agent.tools._get_raw_data', return_value=mock_cot_data)
    mocker.patch('vix_agent.tools._get_vix_raw_data', return_value=mock_vix_data)


    # --- 1. SETUP EXPECTED DATA AND FILE I/O ---

    # Define the file path the tool will create and return.
    expected_raw_uri = "./temp_data/raw_data_test.csv"
    
    # Manually execute the ingestion tool to create the file on disk.
    # The tool's return value (the URI) is ignored in this manual call.
    ingestion_tool("Gold Futures") 
    
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
    
    # Consume the async generator
    final_events = [event async for event in final_events_generator]

    # Retrieve the final session state
    final_session = await session_service.get_session( 
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    final_state = final_session.state
    
    print("\n\n--- DEBUGGING: Ingestion Pipeline ---")

    # =========================================================================
    # 4. ASSERT: Tool Output Verification
    # =========================================================================

    # Check 1: Tool Caller Output. The URI is saved to 'ingestion_raw_output' via the agent's output_key.
    raw_uri_string_output = final_state.get('ingestion_raw_output')
    print(f"DEBUG 1: 'ingestion_raw_output' context key value (URI string): '{raw_uri_string_output}'")
    
    # This assertion verifies the LlmAgent successfully captured the tool's return value (the URI).
    assert raw_uri_string_output == expected_raw_uri
    print("✅ CHECK 1: Ingestion Tool's URI output was successfully saved to context.")
    
    

    #######  Checking Feature Agent#############
    expected_feature_uri = "./temp_data/engineered_data.csv"
    
    # =========================================================================
    # 6. ASSERT: Tool Output Verification
    # =========================================================================

    # Check 1: Tool Caller Output. The URI is saved to 'ingestion_raw_output' via the agent's output_key.
    feature_uri_string_output = final_state.get('feature_tool_raw_output')
    print(f"DEBUG 3: 'feature _output' context key value (URI string): '{feature_uri_string_output}'")
    
    # This assertion verifies the LlmAgent successfully captured the tool's return value (the URI).
    assert feature_uri_string_output == expected_feature_uri
    print("✅ CHECK 3: Ingestion Tool's URI output was successfully saved to context.")
    

    

@pytest.mark.asyncio
async def test_pipeline_data_flow_and_pydantic_output(mocker, 
                                                           mock_vix_data, 
                                                           mock_cot_data,
                                                           cot_workflow_runner):
    """
    Tests the pipeline execution, verifying state passing and Pydantic validation 
    for the ingestion stage using the output_key mechanism.
    """
    runner, session_service = cot_workflow_runner 
    session_id = "test_session_123"
    user_id = "test_user"
    app_name = "COTAnalysisTradingApp"
    test_prompt = "Start the trading signal generation workflow for Gold Futures now."
    mocker.patch('vix_agent.tools._get_raw_data', return_value=mock_cot_data)
    mocker.patch('vix_agent.tools._get_vix_raw_data', return_value=mock_vix_data)


    # --- 1. SETUP EXPECTED DATA AND FILE I/O ---

    # Define the file path the tool will create and return.
    expected_raw_uri = "./temp_data/raw_data_test.csv"
    
    # Manually execute the ingestion tool to create the file on disk.
    # The tool's return value (the URI) is ignored in this manual call.
    ingestion_tool("Gold Futures") 
    
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
    
    # Consume the async generator
    final_events = [event async for event in final_events_generator]

    # Retrieve the final session state
    final_session = await session_service.get_session( 
        app_name=app_name,
        user_id=user_id,
        session_id=session_id
    )
    final_state = final_session.state
    
    print("\n\n--- DEBUGGING: Ingestion Pipeline ---")

    # =========================================================================
    # 4. ASSERT: Tool Output Verification
    # =========================================================================

    # Check 1: Tool Caller Output. The URI is saved to 'ingestion_raw_output' via the agent's output_key.
    raw_uri_string_output = final_state.get('ingestion_raw_output')
    print(f"DEBUG 1: 'ingestion_raw_output' context key value (URI string): '{raw_uri_string_output}'")
    
    # This assertion verifies the LlmAgent successfully captured the tool's return value (the URI).
    assert raw_uri_string_output == expected_raw_uri
    print("✅ CHECK 1: Ingestion Tool's URI output was successfully saved to context.")
    
    #######  Checking Feature Agent#############
    expected_feature_uri = "./temp_data/engineered_data.csv"
    
    # =========================================================================
    # 6. ASSERT: Tool Output Verification
    # =========================================================================

    # Check 1: Tool Caller Output. The URI is saved to 'ingestion_raw_output' via the agent's output_key.
    feature_uri_string_output = final_state.get('feature_tool_raw_output')
    print(f"DEBUG 3: 'feature _output' context key value (URI string): '{feature_uri_string_output}'")
    
    # This assertion verifies the LlmAgent successfully captured the tool's return value (the URI).
    assert feature_uri_string_output == expected_feature_uri
    print("✅ CHECK 3: Ingestion Tool's URI output was successfully saved to context.")
    
    ### SIGNAL TOOL
    # #######  Checking Feature Agent#############
    market = "Gold Futures"
    expected_signal_uri = f"./temp_data/signal_output_{market.replace(' ', '_').lower()}.json" 
    
    # =========================================================================
    # 8. ASSERT: Tool Output Verification
    # =========================================================================

    # Check 1: Tool Caller Output. The URI is saved to 'ingestion_raw_output' via the agent's output_key.
    signal_uri_string_output = final_state.get('signal_file_uri_raw')
    print(f"DEBUG 5: 'signal _output' context key value (URI string): '{signal_uri_string_output}'")
    
    # This assertion verifies the LlmAgent successfully captured the tool's return value (the URI).
    print(f'signal outp ut is :{signal_uri_string_output} vs expected {expected_signal_uri}')
    assert signal_uri_string_output == expected_signal_uri
    print("✅ CHECK 5: Signal Tool's URI output was successfully saved to context.")
    
    
    import json

    # Read the actual JSON file content
    with open(expected_signal_uri , 'r') as f:
        file_content_data = json.load(f)

    print(f'==== PYTEST SIGNL OUT :{file_content_data}')


    # SIGNAL MODEL TEST
    #### FEATURE MODEL
    # =========================================================================
    # 7. ASSERT: Feature Pydantic Model Generation
    # =========================================================================

    # Check 5: Model Generator Output (Should hold the final Pydantic DataPointerModel dict)
    signal_model_data = final_state.get('final_signal_json')
    print(f"DEBUG 6: 'final_signal_json' context key value (Pydantic dict): {signal_model_data}")
    
    # Check 6: Pydantic Validation 
    assert signal_model_data is not None

    print(f'text vix agent, signal mdoel data from {signal_uri_string_output}====================== {signal_model_data}')

    try:
        signal_model = SignalDataModel(**signal_model_data)
    except Exception as e:
        pytest.fail(f"SignalDataModel validation failed: {e}")
        
    assert signal_model.market == market
    # Assuming DataPointerModel now includes 'market'
    assert signal_model.signal == "Neutral"
    assert signal_model.confidence == 0.4
    print("✅ CHECK 6: Final SignalDataModelel validated.")

    