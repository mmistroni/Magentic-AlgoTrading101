from google.adk.agents import LlmAgent
# Flight Agent
fagent = LlmAgent(
    model='gemini-2.0-flash',
    name="FlightAgent",
    description="Flight booking agent",
    instruction="I am an agent"
)