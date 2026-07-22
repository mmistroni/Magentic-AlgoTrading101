# agents/congress_trades_agent/congress_trades_agent/utils/pipeline_runner.py

import asyncio
from google.adk import App
from google.adk.runners import InMemoryRunner

# Relative import to pull your existing root_agent
from ..agent import root_agent

async def run_agent_pipeline(prompt: str) -> str:
    """Programmatically executes the ADK agent and returns its text output."""
    app = App(name="congress_alpha_app", root_agent=root_agent)
    
    async with InMemoryRunner(app=app) as runner:
        events = await runner.run_debug(
            user_message=prompt,
            verbose=False
        )
        
        final_text = ""
        for event in events:
            if hasattr(event, "content") and event.content:
                final_text = event.content
                
        return final_text

if __name__ == "__main__":
    test_prompt = "Current Analysis Date: 2026-07-01. Execute Congress Alpha Strategy for FN."
    result = asyncio.run(run_agent_pipeline(test_prompt))
    print("\n--- PIPELINE OUTPUT ---")
    print(result)