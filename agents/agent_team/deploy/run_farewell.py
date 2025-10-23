# @title Define and Test GPT Agent
import os
import asyncio
from google.adk.agents import Agent
from google.adk.models.lite_llm import LiteLlm # For multi-model support
from google.adk.sessions import InMemorySessionService
from google.adk.runners import Runner
from google.genai import types # For cr
# Make sure 'get_weather' function from Step 1 is defined in your environment.
# Make sure 'call_agent_async' is defined from earlier.
from agent_team.farewell_agent import farewell_agent
from agent_team.utils import call_agent_async
# --- Agent using GPT-4o ---
weather_agent_gpt = None # Initialize to None
runner_gpt = None      # Initialize runner to None


async def run_conversation():

    try:
        weather_agent_gpt = farewell_agent
        print(f"Agent '{weather_agent_gpt.name}' created using model .")

        # InMemorySessionService is simple, non-persistent storage for this tutorial.
        session_service_gpt = InMemorySessionService() # Create a dedicated service

        # Define constants for identifying the interaction context
        APP_NAME_GPT = "weather_tutorial_app_gpt" # Unique app name for this test
        USER_ID_GPT = "user_1_gpt"
        SESSION_ID_GPT = "session_001_gpt" # Using a fixed ID for simplicity

        # Create the specific session where the conversation will happen
        session_gpt = await session_service_gpt.create_session(
            app_name=APP_NAME_GPT,
            user_id=USER_ID_GPT,
            session_id=SESSION_ID_GPT
        )
        print(f"Session created: App='{APP_NAME_GPT}', User='{USER_ID_GPT}', Session='{SESSION_ID_GPT}'")

        # Create a runner specific to this agent and its session service
        runner_gpt = Runner(
            agent=weather_agent_gpt,
            app_name=APP_NAME_GPT,       # Use the specific app name
            session_service=session_service_gpt # Use the specific session service
            )
        print(f"Runner created for agent '{runner_gpt.agent.name}'.")

        # --- Test the GPT Agent ---
        print("\n--- Testing GPT Agent ---")
        # Ensure call_agent_async uses the correct runner, user_id, session_id
        await call_agent_async(query = "I am thinking of leavinng..?",
                            runner=runner_gpt,
                            user_id=USER_ID_GPT,
                            session_id=SESSION_ID_GPT)
        # --- OR ---

        # Uncomment the following lines if running as a standard Python script (.py file):
        # import asyncio
        # if __name__ == "__main__":
        #     try:
        #         asyncio.run(call_agent_async(query = "What's the weather in Tokyo?",
        #                      runner=runner_gpt,
        #                       user_id=USER_ID_GPT,
        #                       session_id=SESSION_ID_GPT)
        #     except Exception as e:
        #         print(f"An error occurred: {e}")

    except Exception as e:
        print(f"❌ Could not create or run GPT agent #. Check API Key and model name. Error: {e}")



# Uncomment the following lines if running as a standard Python script (.py file):
import asyncio
if __name__ == "__main__":
    try:
        asyncio.run(run_conversation())
    except Exception as e:
        print(f"An error occurred: {e}")