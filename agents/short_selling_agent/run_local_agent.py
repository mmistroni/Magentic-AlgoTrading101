import argparse
from pathlib import Path
from google.adk.runners import InMemoryRunner
from google.adk.cli.utils.agent_loader import AgentLoader
from google.genai.types import Content, Part

# 1. Setup mandatory command-line arguments first
parser = argparse.ArgumentParser(
    description="Run the ADK 2.0 short-selling pipeline with a mandatory target date."
)
parser.add_argument(
    "--run-date",
    required=True,
    help="The target execution date in YYYY-MM-DD format (e.g., 2026-07-10)"
)
args = parser.parse_args()

# 2. Adjust path to look for the nested folder in the current directory context
AGENTS_DIR = Path(".").resolve()

# Initialize the loader pointing to the current directory context
loader = AgentLoader(agents_dir=str(AGENTS_DIR))
agent_app = loader.load_agent("short_selling_agent")

print("--- Starting ADK 2.0 Pipeline Run ---")

# 3. Build the local runner
runner = InMemoryRunner(
    agent=agent_app,
    app_name="short_selling_agent"
)

# 4. Target the correct internal memory storage layout to pre-register the session
session_id = "short_test_session"
user_id = "local_dev"

print(f"📦 Seeding internal session store registry for: '{session_id}'...")
runner.session_store.create_session(user_id=user_id, session_id=session_id)

# 5. Instantiate explicit strongly-typed 2.0 objects using the CLI provided date
structured_message = Content(
    role="user",
    parts=[Part(text=f"Run the short-selling pipeline for {args.run_date}.")]
)

# 6. Execute the interaction passing the structural typing frame
response_stream = runner.run(
    user_id=user_id,
    session_id=session_id,
    new_message=structured_message
)

print(f"\nFinal Output for {args.run_date}: \n")

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