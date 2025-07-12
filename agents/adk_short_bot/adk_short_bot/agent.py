from google.adk.agents import Agent
from adk_short_bot.prompts import ROOT_AGENT_INSTRUCTION
from adk_short_bot.tools.character_counter import count_characters

root_agent = Agent(
    name="adk_short_bot",
    model="gemini-2.0-flash",
    description="A bot that shortens messages while maintaining their core meaning",
    instruction=ROOT_AGENT_INSTRUCTION,
    tools=[count_characters],
)

# --- The ONLY new part you need to add to this file ---
def create_agent() -> Agent: # Or just `-> Agent:` if LlmAgent isn't needed for type hint
    """
    Returns the instantiated adk_gsheet_agent.
    This function acts as the entry point for Agent Engine deployments
    and local 'adk web' execution when using --target.
    """
    print("create_agent() called: Returning the pre-initialized root_agent.")
    return root_agent

# Optional: Keep your local testing block if you have one
# if __name__ == "__main__":
#    print("Running local test of create_agent()...")
#    my_agent = create_agent()
#    print(f"Agent name: {my_agent.name}")
#    print(my_agent.call("Hello from local test!"))




