# Copyright 2025 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Test cases for the Academic Research."""

import textwrap

import dotenv
import pytest
from multi_agent.flight_agent import fagent
from google.adk.runners import InMemoryRunner
from google.genai import types
from google.genai.types import Tool
pytest_plugins = ("pytest_asyncio",)


@pytest.fixture(scope="session", autouse=True)
def load_env():
    dotenv.load_dotenv()


@pytest.mark.asyncio
async def test_happy_path():
    """Runs the agent on a simple input and expects a normal response."""
    user_input = textwrap.dedent(
        """
        I want you to book me a flight to paris.
    """
    ).strip()

    app_name = "agent_team"

    runner = InMemoryRunner(agent=fagent, app_name=app_name)
    session = await runner.session_service.create_session(
        app_name=runner.app_name, user_id="test_user"
    )
    content = types.Content(parts=[types.Part(text=user_input)])
    response_received = False
    async for event in runner.run_async(
        user_id=session.user_id,
        session_id=session.id,
        new_message=content
    ):
        print(f'Event is n{event}')
        if event.content and event.content.parts and event.content.parts[0].text:
            response_received = True
            break # Exit loop as soon as a response is found

    # Assert that at least one response was received
    assert response_received, "The agent did not provide any response."