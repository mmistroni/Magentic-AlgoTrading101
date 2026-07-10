import os
import asyncio
from pathlib import Path
from google.adk.runners import InMemoryRunner
from google.adk.cli.utils.agent_loader import AgentLoader
from google.genai.types import Content, Part

# 1. Hardcode the source directory root for your agents block
AGENTS_DIR = Path("/workspaces/Magentic-AlgoTrading101/agents")

async def main():
    # 2. Initialize the 2.0 loader context
    loader = AgentLoader(agents_dir=str(AGENTS_DIR))
    agent_app = loader.load_agent("short_selling_agent")

    # 3. Build the local memory runner
    runner = InMemoryRunner(
        agent=agent_app,
        app_name="short_selling_agent"
    )

    # 4. EXPLICITLY CREATE THE SESSION BEFORE RUNNING THE AGENT
    # This registers the session inside the runner's isolated memory pool
    print("--- Creating Local ADK 2.0 Session ---")
    await runner.session_service.create_session(
        app_name="short_selling_agent",
        user_id="local_dev",
        session_id="short_test_session"
    )

    print("--- Starting ADK 2.0 Pipeline Run ---")

    # 5. Instantiate explicit strongly-typed 2.0 content object
    structured_message = Content(
        role="user",
        parts=[Part(text="Run the short-selling pipeline for 2026-07-09.")]
    )

    # 6. Execute the interaction (returns an async generator stream)
    response_stream = runner.run(
        user_id="local_dev",
        session_id="short_test_session",
        new_message=structured_message
    )

    print("\nFinal Output: \n")

    # 7. Consume and print the stream event steps cleanly
    for event in response_stream:
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                print(event.content.parts[0].text, end="", flush=True)
        elif hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts") and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text, end="", flush=True)
    print()

if __name__ == "__main__":
    # Run the orchestrator script using the standard asyncio loop wrapper
    asyncio.run(main())