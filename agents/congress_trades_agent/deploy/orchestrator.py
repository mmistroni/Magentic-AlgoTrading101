# main.py
import os
import json
import vertexai
from vertexai.generative_models import (
    GenerativeModel, 
    Tool, 
    AutomaticFunctionCallingConfig,
    GenerationConfig
)
from src import tools
from src import prompts

# CONFIG
PROJECT_ID = os.environ.get("PROJECT_ID", "your-project-id")
LOCATION = "us-central1"

def run_agent(target_date: str):
    vertexai.init(project=PROJECT_ID, location=LOCATION)

    # 1. Define the Model with Tools
    model = GenerativeModel(
        "gemini-1.5-pro-001",
        tools=[
            Tool.from_function(tools.fetch_congress_signals_tool),
            Tool.from_function(tools.check_fundamentals_tool)
        ],
        system_instruction=prompts.TRADER_INSTRUCTION
    )

    # 2. Define the Chat (Memory needed for context)
    chat = model.start_chat()

    # 3. Step 1: Researcher (Optional, or simulated here for simplicity)
    # In a full pipeline, you'd run the Researcher Agent here.
    # For now, let's assume a generic context or ask the Trader to assume Neutral context
    political_context = "Neutral context. No major bills passed this month." 

    # 4. Step 2: Send the Prompt to the Trader
    print(f"🚀 Starting Analysis for {target_date}...")
    
    user_prompt = f"""
    CURRENT DATE: {target_date}
    POLITICAL CONTEXT: {political_context}
    
    Execute your protocol. Check signals, then check fundamentals, then synthesize.
    """

    response = chat.send_message(
        user_prompt,
        tool_config=AutomaticFunctionCallingConfig(disable_automatic_function_calling=False),
        generation_config=GenerationConfig(
            temperature=0.1, # Keep it analytical
            response_mime_type="application/json" # Force JSON output
        )
    )

    # 5. Output Result
    try:
        decisions = json.loads(response.text)
        print("\n✅ AGENT DECISIONS:")
        print(json.dumps(decisions, indent=2))
        
        # Here is where you would call `save_to_bigquery(decisions)`
        
    except Exception as e:
        print(f"❌ Error parsing agent output: {response.text}")

if __name__ == "__main__":
    # Default to a date where you know you have data (e.g., Nov 30 if data starts Nov 1)
    target_date = os.environ.get("ANALYSIS_DATE", "2024-11-30")
    run_agent(target_date)