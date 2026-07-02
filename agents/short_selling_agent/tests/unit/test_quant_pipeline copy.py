import json
import pytest
from google import adk

# Import your production prompt string
from short_selling_agent.prompts import QUANT_COORDINATOR_INSTRUCTIONS

import pytest
from google.adk import Agent
from pydantic import BaseModel, Field

# 1. Define a structured schema for your short-selling analysis
class ShortSellingAnalysis(BaseModel):
    ticker: str = Field(description="The stock ticker symbol.")
    signal: str = Field(description="The trade signal, e.g., BEARISH, NEUTRAL, BULLISH.")
    rationale: str = Field(description="Core fundamental or technical justification.")

# 2. Instantiate your specific orchestrator agent
orchestrator_agent = Agent(
    name="short_selling_orchestrator",
    model="gemini-2.5-flash",
    instruction=QUANT_COORDINATOR_INSTRUCTIONS,
    # Optional: If you have tools built out, you'd register them here: tools=[fetch_market_data]
)

# 3. The Unit Test
def test_orchestrator_agent_response():
    """Test that the orchestrator agent runs and returns a structured response."""
    
    # Create an isolated session for this test run
    session = orchestrator_agent.create_session(session_id="test_short_sale_01")
    
    # Define a mock market scenario for the agent to process
    test_prompt = (
        "Evaluate Tesla (TSLA). Fundamentals: P/E ratio is historically overextended, "
        "and insider selling has spiked. Technicals: It just broke below its 50-day "
        "moving average on heavy volume."
    )
    
    # Send the message and enforce your Pydantic schema output shape
    response = session.send_message(
        test_prompt,
        response_schema=ShortSellingAnalysis
    )
    
    # 4. Assertions to validate the execution
    assert response is not None, "Agent returned an empty response object."
    assert response.text != "", "Agent response text is empty."
    
    # If using ADK's built-in schema handling, parse and verify the structured output
    structured_data = response.parsed_content
    assert isinstance(structured_data, ShortSellingAnalysis)
    assert structured_data.ticker == "TSLA"
    assert structured_data.signal == "BEARISH"