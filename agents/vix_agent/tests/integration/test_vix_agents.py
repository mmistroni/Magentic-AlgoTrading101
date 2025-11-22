import pytest
import os
import shutil
from pydantic import BaseModel, Field
from google.adk.agents import LlmAgent, SequentialAgent, Context
from vix_agent.models import DataPointerModel, SignalDataModel, FeatureDataModel
from vix_agent.vix_agents import FEATURE_AGENT, INGESTION_AGENT, SIGNAL_AGENT

@pytest.fixture(scope="module")
def cleanup_temp_data():
    """Fixture to ensure the temp_data directory is cleaned before and after tests."""
    temp_dir = "./temp_data"
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)
    os.makedirs(temp_dir, exist_ok=True)
    yield # Test runs here
    if os.path.exists(temp_dir):
        shutil.rmtree(temp_dir)

@pytest.fixture
def cot_workflow_agent(cleanup_temp_data):
    """Fixture to create and return the SequentialAgent using imported agents."""
    # NOTE: These agents (INGESTION_AGENT, etc.) are assumed to be imported from vix_agents.py
    # and are mocked for this script.
    return SequentialAgent(
        name="COTAnalysisWorkflow",
        sub_agents=[
            INGESTION_AGENT,
            FEATURE_AGENT,
            SIGNAL_AGENT
        ]
    )

@pytest.fixture
def initial_adk_context():
    """Fixture to create the initial ADK Context."""
    return Context(market='Gold Futures')

def test_pipeline_data_flow_and_pydantic_output(cot_workflow_agent, initial_adk_context):
    """
    Tests sequential execution, context passing (URI check), and Pydantic output.
    """
    test_prompt = "Start the trading signal generation workflow for Gold Futures now."
    
    # ACT: Run the SequentialAgent
    final_context = cot_workflow_agent.run(
        context=initial_adk_context, 
        prompt=test_prompt
    )
    
    print("\n\n--- Running Pipeline Integration Test ---")

    # 1. ASSERT: Context Passing (URI Pointers)
    raw_pointer = final_context.get('raw_data_pointer')
    feature_pointer = final_context.get('feature_data_pointer')
    
    # Check 1: Ingestion Agent Output
    assert isinstance(raw_pointer, DataPointerModel)
    assert raw_pointer.uri == "./temp_data/raw_data_test.csv"
    print(f"✅ Ingestion Agent: Raw data URI passed successfully: {raw_pointer.uri}")

    # Check 2: Feature Agent Output
    assert isinstance(feature_pointer, DataPointerModel)
    assert feature_pointer.uri == "./temp_data/engineered_data.csv"
    print(f"✅ Feature Agent: Engineered data URI passed successfully: {feature_pointer.uri}")

    # 2. ASSERT: Final Pydantic Output (from SIGNAL_AGENT)
    final_result = final_context.get('final_output')

    # Check 3: Signal Agent Output
    assert isinstance(final_result, SignalDataModel)
    assert final_result.signal == "Buy"
    print(f"✅ Signal Agent: Final output is correct ({final_result.signal}) and Pydantic validated.")
    print(f"   Reason: {final_result.reason}")

# To run this test:
# 1. Save the entire code block as 'test_pipeline_pytest.py'.
# 2. Run the command: 'pytest test_pipeline_pytest.py