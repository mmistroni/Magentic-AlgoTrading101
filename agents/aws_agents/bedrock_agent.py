from strands import Agent, tool
from strands_tools import calculator # Import the calculator tool
import argparse
import json
from strands.models import BedrockModel
from bedrock_agentcore.runtime import BedrockAgentCoreApp

# Create a custom tool 
@tool
def weather():
    """ Get weather """ # Dummy implementation
    return "sunny"
app = BedrockAgentCoreApp()
agent = None


def create_agent():

    model_id = "global.anthropic.claude-haiku-4-5-20251001-v1:0"
    model = BedrockModel(
        model_id=model_id,
    )
    tools=[calculator, weather]
    
    return Agent(
            model=model,
            tools = tools
            #system_prompt="You're a helpful assistant. You can do simple math calculation, and tell the weather."
    )

@app.entrypoint
async def invoke(payload, context):
    """
    Invoke the agent with a payload
    """
    global agent
    user_message = payload.get("prompt")
    _ = payload["actor_id"]

    session_id = context.session_id

    if not agent:
        agent = create_agent()

    if not session_id:
        raise Exception("Content session id is not set")

    async for event in agent.stream_async(user_message):
        if "data" in event:
            yield event["data"]

if __name__ == "__main__":
    app.run()