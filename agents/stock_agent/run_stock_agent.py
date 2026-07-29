import argparse
import asyncio
import re
from pathlib import Path
from google.adk.runners import InMemoryRunner
from google.adk.cli.utils.agent_loader import AgentLoader
from google.genai.types import Content, Part


def validate_date_format(date_str: str) -> str:
    """Validates that the provided date string strictly follows YYYY-MM-DD format."""
    pattern = r"^\d{4}-\d{2}-\d{2}$"
    if not re.match(pattern, date_str):
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{date_str}'. Date must be strictly in YYYY-MM-DD format (e.g., 2026-07-29)."
        )
    return date_str


# ==========================================
# 1. Command-Line Argument Setup
# ==========================================
parser = argparse.ArgumentParser(
    description="Run the ADK Stock Quantitative Analysis Pipeline with a required YYYY-MM-DD execution date."
)

parser.add_argument(
    "--target-date",
    required=True,
    type=validate_date_format,
    help="MANDATORY: Target snapshot date in YYYY-MM-DD format (e.g., 2026-07-29)."
)

parser.add_argument(
    "--agent-dir",
    default=".",
    help="Path to the directory containing the agent package. Defaults to current directory."
)

args = parser.parse_args()


async def main():
    # ==========================================
    # 2. Agent Loading
    # ==========================================
    AGENTS_DIR = Path(args.agent_dir).resolve()
    print(f"🔍 Loading agent package from: {AGENTS_DIR}")

    loader = AgentLoader(agents_dir=str(AGENTS_DIR))
    agent_app = loader.load_agent("stock_agent")

    print("--- Starting ADK 2.0 Stock Agent Pipeline Run ---")

    # ==========================================
    # 3. Local Runner & Async Session Setup
    # ==========================================
    runner = InMemoryRunner(
        agent=agent_app,
        app_name="stock_agent"
    )

    session_id = "stock_agent_dev_session"
    user_id = "local_quant_dev"

    print(f"📦 Creating session asynchronously for: '{session_id}' (User: '{user_id}')...")
    
    # CRITICAL FIX: Session creation MUST be awaited!
    await runner.session_service.create_session(
        app_name=runner.app_name,
        user_id=user_id,
        session_id=session_id
    )

    # ==========================================
    # 4. Structured Message Payload
    # ==========================================
    prompt_text = (
        f"Execute the full schema discovery and quantitative trend analysis "
        f"for market snapshot date: {args.target_date}."
    )

    structured_message = Content(
        role="user",
        parts=[Part(text=prompt_text)]
    )

    # ==========================================
    # 5. Pipeline Execution & Output Streaming
    # ==========================================
    print(f"🚀 Executing TREND_PIPELINE for target date: '{args.target_date}'...\n")


    # Use run_async within the event loop
    response_stream = runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=structured_message
    )

    print(f"--- Pipeline Output for {args.target_date} ---\n")

    async for event in response_stream:
        if hasattr(event, "is_final_response") and event.is_final_response():
            if event.content and event.content.parts:
                print(event.content.parts[0].text, end="", flush=True)
        elif hasattr(event, "content") and event.content:
            if hasattr(event.content, "parts") and event.content.parts:
                for part in event.content.parts:
                    if hasattr(part, "text") and part.text:
                        print(part.text, end="", flush=True)

    print("\n\n--- Run Complete ---")


if __name__ == "__main__":
    asyncio.run(main())