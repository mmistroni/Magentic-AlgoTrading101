ROOT_AGENT_INSTRUCTION = """
You are a helpful assistant that can use the following tools:
- get_current_time.
The user will ask you for the current time and you must answer
using the tools at your disposal.
"""
ROOT_WEATHER_AGENT = """You are a helpful weather assistant. 
                     When the user asks for the weather in a specific city, 
                     use the 'get_weather' tool to find the information. 
                     If the tool returns an error, inform the user politely. 
                     If the tool is successful, present the weather report clearly."""



# --- Define Model Constants for easier use ---

# More supported models can be referenced here: https://ai.google.dev/gemini-api/docs/models#model-variations
MODEL_GEMINI_2_0_FLASH = "gemini-2.0-flash"

# More supported models can be referenced here: https://docs.litellm.ai/docs/providers/openai#openai-chat-completion-models
MODEL_GPT_4O = "openai/gpt-4.1" # You can also try: gpt-4.1-mini, gpt-4o etc.

# More supported models can be referenced here: https://docs.litellm.ai/docs/providers/anthropic
MODEL_CLAUDE_SONNET = "anthropic/claude-sonnet-4-20250514" # You can also try: claude-opus-4-20250514 , claude-3-7-sonnet-20250219 etc
