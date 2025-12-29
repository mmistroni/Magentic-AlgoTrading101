import pytest
import os
import shutil

from google.genai import types
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from pytest import approx
# 1. Import the main pipeline
from stock_agent.stock_agents import TREND_PIPELINE 
from stock_agent.models import TechnicalSchema
# 2. Import the ingestion tool for manual file creation
from stock_agent.tools import discover_technical_schema_tool, fetch_technical_snapshot_tool
import pandas as pd
from pathlib import Path
import re
from typing import Union, Optional
from stock_agent.stock_agents import SCHEMA_FORMATTER_AGENT

# -----------------------------------------------------------------------------
# --- FIXTURES ---
# -----------------------------------------------------------------------------
# --- Helper Function for Date Parsing (Include this in your module) ---

@pytest.fixture
def mock_schema_data():
    """Returns a mock schema."""
    real_schema = {'symbol': 'STRING', 'marketCap': 'FLOAT', 'price': 'FLOAT', 
                    'open': 'FLOAT', 'previousClose': 'FLOAT', 'change': 'FLOAT', 
                    'exchange': 'STRING', 'country': 'STRING', 'ticker': 'STRING', 
                    'asodate': 'DATE', 'cob': 'DATE', 'selection': 'STRING', 
                    'ADX': 'FLOAT', 'RSI': 'FLOAT', 'SMA20': 'FLOAT', 'SMA50': 'FLOAT', 
                    'SMA200': 'FLOAT', 'highlight': 'STRING', 'slope': 'INTEGER', 
                    'previous_obv': 'FLOAT', 'current_obv': 'FLOAT', 'previous_cmf': 'FLOAT', 
                    'last_cmf': 'FLOAT', 'obv_last_20_days': 'FLOAT', 'cmf_last_20_days': 'FLOAT'}
    return real_schema

@pytest.fixture
def mock_snapshot_data():
    """Returns a mock snapshot ."""
    current_test_dir = Path(__file__).parent
    file_path = current_test_dir.parent / "resources" / "snapshot_test.csv"

    snapshot_real_df = pd.read_csv(
            file_path, 
            ## You might also need to specify the date format if it's non-standard: 
            # date_parser=lambda x: pd.to_datetime(x, format='%Y-%m-%d')
        )
    
    return snapshot_real_df


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
def trend_workflow_runner(cleanup_temp_data):
    """
    Fixture to create and return the ADK Runner using the *original* imported pipeline.
    """
    session_service = InMemorySessionService()

    # Use the pre-configured pipeline directly 
    test_pipeline = TREND_PIPELINE
    
    # Initialize the Runner
    runner = Runner(
        agent=test_pipeline, 
        session_service=session_service,
        app_name="TrendPipelineApp" 
    )
    
    return runner, session_service

# -----------------------------------------------------------------------------
# --- THE INTEGRATION TEST ---
# -----------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_pipeline_data_ingestion_and_pydantic_output(mocker, 
                                                           mock_schema_data, 
                                                           mock_snapshot_data,
                                                           trend_workflow_runner):
    """
    Tests the pipeline execution, verifying state passing and Pydantic validation 
    for the ingestion stage using the output_key mechanism.
    """
    runner, session_service = trend_workflow_runner 

    mocker.patch('stock_agent.tools.discover_technical_schema_tool', return_value=mock_schema_data)
    mocker.patch('stock_agent.tools.fetch_technical_snapshot_tool', return_value=mock_snapshot_data)

    session_id = "test_session_123"
    user_id = "test_user"
    app_name = "TrendPipelineApp"
    test_prompt = "Provide me the current schema of the table holding the stocks."

    # --- 1. SETUP EXPECTED DATA AND FILE I/O ---

    # Define the file path the tool will create and return.
    expected_raw_uri = "./temp_data/raw_data_test.csv"
    expected_vix_raw_uri = "./temp_data/vix_raw_data_test.csv"


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
    available_schema = final_state.get('available_schema')
    print(f"DEBUG 1: 'schema check'\n:{available_schema}")
    print(type(available_schema))

    assert available_schema is not None
    
    
    metadata_keys_to_check = ['symbol', 'price', 'selection']
    tech_keys_to_check = ["ADX", "RSI", "SMA20", "SMA200", "SMA50"]


    # Re-cast it back to the Pydantic object
    pyd_available_schema = TechnicalSchema.model_validate(available_schema)

    # Check metadata
    for key in metadata_keys_to_check:
        assert key in pyd_available_schema.metadata, f"{key} missing from metadata"

    # Check technical indicators
    for key in tech_keys_to_check:
        assert key in pyd_available_schema.indicators, f"{key} missing from indicators"


@pytest.mark.asyncio
async def test_schema_formatter_logic_buckets(mocker, 
                                                           mock_schema_data, 
                                                           mock_snapshot_data,
                                                           trend_workflow_runner):
    
    """
    Tests the pipeline execution, verifying state passing and Pydantic validation 
    for the ingestion stage using the output_key mechanism.
    """
    runner, session_service = trend_workflow_runner 

    mocker.patch('stock_agent.tools.discover_technical_schema_tool', return_value=mock_schema_data)
    mocker.patch('stock_agent.tools.fetch_technical_snapshot_tool', return_value=mock_snapshot_data)

    session_id = "test_session_123"
    user_id = "test_user"
    app_name = "TrendPipelineApp"
    test_prompt = "Map the schema."
    mock_raw_columns = "ticker, price, RSI, ADX, SMA20, volume, CHOP14, KAMA"
    
    # 2. CREATE AND INITIALIZE THE SESSION
    await session_service.create_session(
        app_name=app_name, 
        session_id=session_id,
        user_id=user_id, 
        state={"raw_discovery_results": mock_raw_columns}
    
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
    available_schema = final_state.get('available_schema')
    print(f"DEBUG 1: 'schema check'\n:{available_schema}")
    print(type(available_schema))

@pytest.mark.asyncio
async def test_debug_formatter_delegation_trace(mocker, 
                                               mock_schema_data, 
                                               trend_workflow_runner):
    """
    DEBUG TEST: Traces the Parent-Child handoff to see why 'available_schema' is None.
    """
    runner, session_service = trend_workflow_runner 

    # Mocking discovery to ensure we have input for the Formatter
    mocker.patch('stock_agent.tools.discover_technical_schema_tool', return_value=mock_schema_data)
    
    session_id = "debug_session_999"
    user_id = "debug_user"
    app_name = "TrendPipelineApp"
    test_prompt = "Run a technical analysis."

    await session_service.create_session(
        app_name=app_name, 
        session_id=session_id,
        user_id=user_id, 
        state={'market': 'Gold Futures'} 
    )
    
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events_generator = runner.run_async( 
        user_id=user_id, 
        session_id=session_id,
        new_message=user_content 
    )

    print("\n" + "="*50)
    print("🕵️ AGENT DELEGATION TRACE")
    print("="*50)

    formatter_called = False
    schema_emitted = False

    async for event in final_events_generator:
        # 1. Trace: Is the Parent even triggering the sub-agent?
        if hasattr(event, 'agent_call'):
            agent_name = event.agent_call.agent_name
            print(f"📍 [STEP 1] Parent is calling sub-agent: {agent_name}")
            if agent_name == "SchemaFormatter":
                formatter_called = True

        # 2. Trace: What is the sub-agent's raw output?
        if hasattr(event, 'model_response') and event.model_response:
            text = event.model_response.text
            print(f"📝 [STEP 2] Sub-Agent Response Text: {text[:100]}...")

        # 3. Trace: Is the State Update actually happening?
        if hasattr(event, 'state_update') and event.state_update:
            updates = event.state_update
            print(f"💾 [STEP 3] State Keys Updated: {list(updates.keys())}")
            if 'available_schema' in updates:
                schema_emitted = True
                print("✅ SUCCESS: available_schema found in event stream!")

    print("="*50)
    
    # Final check of the actual service storage
    final_session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    
    print(f"FINAL VERDICT:")
    print(f"- State Found in Session: {'available_schema' in final_session.state}")

    # The real win is that the data is there!
    assert 'available_schema' in final_session.state, "Schema was never saved to state!"

    # Now verify the CONTENT of the schema
    saved_schema = final_session.state['available_schema']
    assert len(saved_schema.get('indicators', [])) > 0
    print("✅ SUCCESS: The Agent generated the schema correctly!")

@pytest.mark.asyncio
async def test_pipeline_full_run_with_unit(mocker, 
                                           mock_schema_data, 
                                           mock_snapshot_data,
                                           trend_workflow_runner):
    """
    Final Integration Test for the Feature Agent: 
    Verifies the SchemaUnit correctly populates state for the Quant.
    """
    runner, session_service = trend_workflow_runner 

    # Mock the underlying tools
    mocker.patch('stock_agent.tools.discover_technical_schema_tool', return_value=mock_schema_data)
    mock_snapshot = mocker.patch('stock_agent.tools.fetch_technical_snapshot_tool', return_value=mock_snapshot_data)

    session_id = "final_feature_test_session"
    user_id = "test_user"
    app_name = "TrendPipelineApp"
    test_prompt = "Run a technical analysis for today's stock picks."

    # Initialize the session
    await session_service.create_session(
        app_name=app_name, 
        session_id=session_id,
        user_id=user_id, 
        state={'market': 'Gold Futures'} 
    )
    
    # Run the pipeline
    user_content = types.Content(role='user', parts=[types.Part.from_text(text=test_prompt)])
    final_events_generator = runner.run_async( 
        user_id=user_id, 
        session_id=session_id,
        new_message=user_content 
    )
    
    # Trace execution to ensure no steps are skipped
    print("\n🕵️ TRACING EXECUTION...")
    async for event in final_events_generator:
        if hasattr(event, 'agent_call'):
            print(f"-> Calling Agent: {event.agent_call.agent_name}")
        if hasattr(event, 'state_update') and event.state_update:
            if 'available_schema' in event.state_update:
                print("✅ [STATE] available_schema has been committed.")

    # Retrieve final state
    final_session = await session_service.get_session(app_name=app_name, user_id=user_id, session_id=session_id)
    final_state = final_session.state
    
    # --- ASSERTIONS ---
    
    # 1. Verify Schema exists
    available_schema = final_state.get('available_schema')
    assert available_schema is not None, "FAILED: available_schema is still None after Unit execution."
    
    # 2. Verify Pydantic structure
    pyd_schema = TechnicalSchema.model_validate(available_schema)
    assert len(pyd_schema.indicators) > 0, "No indicators found in schema."
    
    # 3. Verify Quant Output
    signal_result = final_state.get('final_trade_signal')
    print(f"📊 FINAL SIGNAL: {signal_result}")
    assert signal_result is not None, "Quant Analyzer failed to generate a signal."

    # 4. Verify the Tool was called with 'today' or 'yesterday'
    mock_snapshot.assert_called()
    