import json
import pytest
from google.adk import Agent

# Import your actual production prompt string from your app file
from short_selling_agent.prompts import QUANT_COORDINATOR_INSTRUCTIONS

# ---------------------------------------------------------------------
# 1. Programmatic Scoring Helper Function
# ---------------------------------------------------------------------
def score_empty_dossier_response(raw_output_text: str) -> float:
    """
    Programmatically grades the agent's output text.
    Returns 1.0 for a perfect match, and 0.0 for a failure.
    """
    try:
        # Strip out any markdown block wrappers if the model returns them
        clean_json_str = raw_output_text.strip().lstrip("```json").rstrip("```").strip()
        data = json.loads(clean_json_str)
        
        # Verify both metric rules are programmatically met
        correct_status = data.get("status") == "No candidates for shorting found"
        empty_decisions = isinstance(data.get("final_decisions"), list) and len(data["final_decisions"]) == 0
        
        if correct_status and empty_decisions:
            return 1.0
            
    except (json.JSONDecodeError, TypeError, KeyError):
        return 0.0
        
    return 0.0


# ---------------------------------------------------------------------
# 2. The Programmatic Pytest Case
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_programmatic_empty_dossier_score():
    """
    Verifies that when the dossier data tool returns an empty object,
    the Quant Coordinator programmatically passes with a perfect accuracy score.
    """
    # Step A: Instantiate the agent directly in memory
    quant_agent = Agent(
        name="quant_coordinator", 
        instruction=QUANT_COORDINATOR_INSTRUCTIONS
    )
    
    # Step B: Programmatically mock the tool interface inside the test
    def mock_read_full_dossier():
        # Force it to return an empty JSON context string
        return "{}"
        
    # Register the mock tool directly over the agent instance
    quant_agent.register_tool(mock_read_full_dossier)
    
    # Step C: Execute the agent logic locally
    context = await quant_agent.execute_local("Process the daily market dossier for 2026-07-01.")
    agent_response = context.get_last_assistant_message()
    
    # Step D: Run your programmatic score evaluator
    accuracy_score = score_empty_dossier_response(agent_response)
    
    print(f"\n📊 Programmatic Accuracy Score: {accuracy_score * 100}%")
    print(f"📝 Raw Model Output:\n{agent_response}")
    
    # Assert that the logic achieves a perfect evaluation score
    assert accuracy_score == 1.0