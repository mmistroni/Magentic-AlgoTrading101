import os
from pathlib import Path
from google.adk.runners import InMemoryRunner
from google.adk.cli.utils.agent_loader import AgentLoader
from google.genai.types import Content, Part

# Hardcode the source directory root for your agents block
AGENTS_DIR = Path("/workspaces/Magentic-AlgoTrading101/agents")

# 1. Initialize the 2.0 loader pointing exactly to the parent 'agents' directory
loader = AgentLoader(agents_dir=str(AGENTS_DIR))
agent_app = loader.load_agent("short_selling_agent")

# 2. Build the local runner with the explicit app_name and auto-creation rules
runner = InMemoryRunner(
    agent=agent_app,
    app_name="short_selling_agent",  # <--- Aligns the framework app name
    auto_create_session=True         # <--- Tells the runner to instantiate the session if missing
)

print("--- Starting ADK 2.0 Pipeline Run ---")

# 3. Instantiate explicit strongly-typed 2.0 objects
structured_message = Content(
    role="user",
    parts=[Part(text="Run the short-selling pipeline for 2026-07-09.")]
)

# 4. Execute the interaction passing the structural typing frame
response_stream = runner.run(
    user_id="local_dev",
    session_id="short_test_session",
    new_message=structured_message
)

print("\nFinal Output: \n")

# 5. Consume and print the stream event steps cleanly
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