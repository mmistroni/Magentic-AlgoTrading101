import pytest
import asyncio
import httpx
import sys
import os
from typing import Dict, Any

# --- 📢 CRITICAL IMPORT FIX for Nested Structure ---
# Add the project root (the directory two levels up) to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..')))

# Import the necessary functions from the client script (must be in the same dir)
from agent_client import (
    run_agent_request, 
    make_request, 
    APP_NAME, 
    USER_ID 
) 
# --- END IMPORT FIX ---

# --- Test Configuration ---
TEST_APP_URL = "http://127.0.0.1:8080"  
TEST_SESSION_ID = "pytest_capital_sim_final" 
# --------------------------

# --- 1. Pytest Fixture for HTTP Client (CORRECTED ASYNC) ---

@pytest.fixture(scope="session")
async def http_client():
    """
    Provides a session-scoped asynchronous HTTP client for all tests.
    FIX: Uses 'async def' and 'async with' to prevent TypeError.
    """
    # 📢 FIX: 'async with' used for asynchronous context management
    async with httpx.AsyncClient(timeout=30.0, base_url=TEST_APP_URL) as client:
        yield client

# --- 2. Pytest Fixture for Session Management (ASYNC) ---

@pytest.fixture(scope="function", autouse=True)
async def agent_session(http_client):
    """Creates and tears down a clean agent session for each test function."""
    current_session_endpoint = f"/apps/{APP_NAME}/users/{USER_ID}/sessions/{TEST_SESSION_ID}"
    session_data = {"state": {"test_mode": True, "source": "pytest_sim"}}

    # SETUP: Clean up and create new session
    try:
        # Use await with the http_client fixture
        await make_request(http_client, "DELETE", current_session_endpoint)
    except Exception:
        pass 
    await make_request(http_client, "POST", current_session_endpoint, data=session_data)
    
    yield TEST_SESSION_ID 

    # TEARDOWN: Delete the session
    await make_request(http_client, "DELETE", current_session_endpoint)


# --- 3. Parameterized Test Cases (Simulation Scenarios) ---

test_scenarios = [
    # Scenario A: Greeting/Purpose Check (Non-Tool)
    # Expected: The agent states its purpose (capital, country).
    ("A_Greeting_Check", 
     "What is your job?", 
     "capital", "country"), 
    
    # Scenario B: Known Tool Success (Input: France, Output: Paris)
    # This tests the agent's ability to call the tool and format the successful response.
    ("B_Tool_Success_France", 
     "What is the capital of France?", 
     "france", "paris"), 
     
    # Scenario C: Known Tool Failure (Input: Spain, Output: "Sorry, I don't know...")
    # This tests the agent's ability to call the tool and handle the tool's explicit failure message.
    ("C_Known_Tool_Failure", 
     "Capital of Spain, please.", 
     "sorry", "spain"), 
    # Scenario D: Refusal Check (Out of Scope)
    # This tests the agent's adherence to its instructions to only discuss capitals.
    ("D_Refusal_Check_Finance", 
     "Tell me about stock markets.", 
     "capital", "cannot"), 
     
    # Scenario E: Another Known Success (Input: Canada, Output: Ottawa)
    # Using 'canada' from the search results to ensure the agent is generalizable beyond the provided sample list.
    ("E_Tool_Success_Canada", 
     "What about Canada's capital?", 
     "canada", "ottawa"), 
]


@pytest.mark.parametrize("test_id, user_input, expected_sub_1, expected_sub_2", test_scenarios)
@pytest.mark.asyncio
async def test_agent_simulation_flow(http_client, agent_session, test_id, user_input, expected_sub_1, expected_sub_2):
    """
    Runs a single parameterized simulation test against the local capital_agent.
    """
    session_id = agent_session
    print(f"\n--- Running Scenario: {test_id} ---")
    
    # Run the request. (Must await the async function)
    final_text = await run_agent_request(http_client, session_id, user_input)
    
    # --- SCORING: Keyword Validation ---
    
    # Check 1: Must include the first expected term (case-insensitive)
    assert expected_sub_1.lower() in final_text.lower(), \
        (f"Test '{test_id}' FAILED on Keyword 1.\n"
         f"Missing: '{expected_sub_1}'. Actual response: '{final_text}'")

    # Check 2: Must include the second expected term (case-insensitive)
    assert expected_sub_2.lower() in final_text.lower(), \
        (f"Test '{test_id}' FAILED on Keyword 2.\n"
         f"Missing: '{expected_sub_2}'. Actual response: '{final_text}'")
        
    print(f"PASS: Scenario '{test_id}' validated successfully.")