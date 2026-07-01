import json
import pytest
from google import adk

# Import your production prompt string
from short_selling_agent.prompts import QUANT_COORDINATOR_INSTRUCTIONS

def score_empty_dossier_response(raw_output_text: str) -> float:
    try:
        clean_json_str = raw_output_text.strip().lstrip("```json").rstrip("```").strip()
        data = json.loads(clean_json_str)
        
        correct_status = data.get("status") == "No candidates for shorting found"
        empty_decisions = isinstance(data.get("final_decisions"), list) and len(data["final_decisions"]) == 0
        
        return 1.0 if (correct_status and empty_decisions) else 0.0
    except (json.JSONDecodeError, TypeError, KeyError):
        return 0.0

# ---------------------------------------------------------------------
# The Corrected Programmatic Pytest Case
# ---------------------------------------------------------------------
@pytest.mark.asyncio
async def test_programmatic_empty_dossier_score():
    """
    Spins up an in-memory execution session directly through the ADK agent.
    """
    
    # 1. Define your mock tool function inside the test context
    def tool_read_full_dossier() -> str:
        return "{}"
    
    # 2. Instantiate the agent using the correct top-level class mapping
    quant_agent = adk.Agent(
        name="quant_coordinator", 
        instruction=QUANT_COORDINATOR_INSTRUCTIONS,
        tools=[tool_read_full_dossier]
    )
    
    # 3. Create an interactive in-memory session directly from the agent
    # This completely eliminates the need to import an "App" class
    session = quant_agent.new_session()
    
    # 4. Asynchronously send the prompt into the session context
    response = await session.send_message(
        "Process the daily market dossier for 2026-07-01."
    )
    
    # 5. Extract the text payload from the response object
    agent_response = response.text
    
    # 6. Score the execution output
    accuracy_score = score_empty_dossier_response(agent_response)
    
    print(f"\n📊 Programmatic Accuracy Score: {accuracy_score * 100}%")
    print(f"📝 Raw Model Output:\n{agent_response}")
    
    assert accuracy_score == 1.0