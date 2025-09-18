FLIGHT_AGENT_INSTRUCTIONS = """You are a flight booking agent...You always return a valid JSON..."""


HOTEL_AGENT_INSTRUCTIONS = """You are a hotel booking agent... You always return a valid JSON..."""


SIGHTSEEING_AGENT_INSTRUCTIONS = """You are a sightseeing agent...You always return a valid JSON..."""

TRIPPLANNER_AGENT_INSTRUCTIONS = """
Act as  a comprehensive trip planner.
- Use the FlightAgent to find and book flights
- Use the HotelAgent to find and book accomodations
- Use the SightSeeingAgent to find information on places to visit
Based on the user request, sequentially invoke all the tools to gather all necessary trip details.
"""

# --- Define Model Constants for easier use ---

# More supported models can be referenced here: https://ai.google.dev/gemini-api/docs/models#model-variations
MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash"

# More supported models can be referenced here: https://docs.litellm.ai/docs/providers/openai#openai-chat-completion-models
MODEL_GPT_4O = "openai/gpt-4.1" # You can also try: gpt-4.1-mini, gpt-4o etc.

# More supported models can be referenced here: https://docs.litellm.ai/docs/providers/anthropic
MODEL_CLAUDE_SONNET = "anthropic/claude-sonnet-4-20250514" # You can also try: claude-opus-4-20250514 , claude-3-7-sonnet-20250219 etc
