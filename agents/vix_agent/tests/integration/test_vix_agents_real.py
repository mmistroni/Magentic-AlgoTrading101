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
from vix_agent.tools import ingestion_tool, _read_data_from_pandas
import pandas as pd
from pathlib import Path
import re
from typing import Union, Optional

# -----------------------------------------------------------------------------
# --- FIXTURES ---
# -----------------------------------------------------------------------------
# --- Helper Function for Date Parsing (Include this in your module) ---
def parse_cftc_report_week(report_week_str: str) -> Optional[pd.Timestamp]:
    """
    Converts a CFTC report string (e.g., '2004 Report Week 30') into a usable Friday date.
    Returns None if parsing fails.
    """
    
    # Use regex to safely extract the Year and the Week Number
    match = re.search(r'(\d{4}) Report Week (\d+)', report_week_str)
    if not match:
        # Return None on failure to align with Optional[pd.Timestamp] hint
        return None 
        
    year = int(match.group(1))
    week_num = int(match.group(2))
    
    try:
        # Construct a string like '2004-30-5' (Year-WeekNumber-DayOfWeek Friday=5)
        # Using ISO week format (%W) for consistency.
        date_str = f"{year}-{week_num}-5"
        
        # When errors='coerce' is used, pd.to_datetime returns pd.NaT on failure,
        # which pandas correctly handles when applied to a series.
        date_result = pd.to_datetime(date_str, format='%Y-%W-%w', errors='coerce') 
        
        # We explicitly check for NaT and convert to None if necessary, 
        # though pd.apply often handles the pd.NaT return fine.
        if pd.isna(date_result):
            return None
            
        return date_result
        
    except ValueError:
        # Catch cases where the week number might be invalid for the year
        return None # Return None on exception

# --- No changes needed to clean_and_standardize_cot_data (it will correctly 
# handle the NaNs resulting from the parse function when applied to the Series) ---
# --- Core Ingestion Agent Logic Snippet ---

def clean_and_standardize_cot_data(raw_cot_df: pd.DataFrame) -> pd.DataFrame:
    """
    Transforms the 'report_week' column to a DateTime index and selects necessary columns.
    This is run inside the COT Ingestion Agent.
    """
    print("COT Ingestion: Cleaning and standardizing report dates and columns...")
    
    # 1. Create a new 'Date' column by applying the parsing function
    raw_cot_df['Date'] = raw_cot_df['report_week'].apply(parse_cftc_report_week)
    
    # 2. Set the clean Date column as the DataFrame index
    raw_cot_df.set_index('Date', inplace=True)
    
    # 3. Drop the original string column and any rows that couldn't be parsed
    raw_cot_df.drop(columns=['report_week'], inplace=True)
    raw_cot_df.dropna(subset=['comm_positions_long_all', 'comm_positions_short_all'], inplace=True)
    
    # 4. Filter down to only the columns needed by the Feature Agent
    # This reduces file size and complexity.
    final_clean_df = raw_cot_df[[
        'comm_positions_long_all', 
        'comm_positions_short_all'
        # Add any other columns the Feature Agent might need (e.g., open_interest)
    ]].copy()
    
    # 5. Ensure position columns are numeric before saving
    final_clean_df['comm_positions_long_all'] = pd.to_numeric(final_clean_df['comm_positions_long_all'], errors='coerce')
    final_clean_df['comm_positions_short_all'] = pd.to_numeric(final_clean_df['comm_positions_short_all'], errors='coerce')

    print(f"COT Ingestion: Clean data shape: {final_clean_df.shape}")
    
    # The Ingestion Agent would now save this final_clean_df (indexed by Date)
    return final_clean_df


@pytest.fixture
def mock_vix_data():
    """Returns a mock DataFrame for the daily VIX price data."""
    current_test_dir = Path(__file__).parent
    file_path = current_test_dir.parent / "resources" / "vix.csv"

    vix_real_df = pd.read_csv(
            file_path, 
            index_col='date', 
            parse_dates=True
            # You might also need to specify the date format if it's non-standard: 
            # date_parser=lambda x: pd.to_datetime(x, format='%Y-%m-%d')
        )
    return vix_real_df

@pytest.fixture
def mock_cot_data():
    """Returns a mock DataFrame for the weekly COT data, forcing an extreme rank."""
    current_test_dir = Path(__file__).parent
    file_path = current_test_dir.parent / "resources" / "cot.csv"

    cot_real_df = pd.read_csv(
            file_path, 
            ## You might also need to specify the date format if it's non-standard: 
            # date_parser=lambda x: pd.to_datetime(x, format='%Y-%m-%d')
        )
    
    cleaned_cot_df = clean_and_standardize_cot_data(cot_real_df)

    return cleaned_cot_df


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
    
    # Checking vix output
    vix_uri_string_output = final_state.get('vix_raw_output_uri')
    assert vix_uri_string_output is not None
    


    # Checking merge outpuot
    merge_uri_string_output = final_state.get('vix_cot_merged_output_uri')
    assert merge_uri_string_output is not None

    merges = _read_data_from_pandas(merge_uri_string_output)

    print(f"---- Test Vix AGent. Merge  is:{merges.head(4)}")
    
    from pprint import pprint
    pprint(merges.head(5))
    
    features_output_uri = final_state.get('feature_tool_raw_output')
    assert features_output_uri is not None
    print(f'[PYTEST]:Feature uri is {features_output_uri}')
    featured = _read_data_from_pandas(features_output_uri)

    print(f"---- FEatured Vix AGent. Merge  is:{featured.tail(4)}")
    

