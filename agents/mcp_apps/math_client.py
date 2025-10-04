from mcp import ClientSession, StdioServerParameters
from mcp.client.stdio import stdio_client
from langchain_mcp_adapters.tools import load_mcp_tools
from langchain_mcp_adapters.tools import load_mcp_tools
from langgraph.prebuilt import create_react_agent
import asyncio

from langchain_openai import ChatOpenAI

server_params = StdioServerParameters(
  command="python",
  args=["math_server.py"],
)


model = ChatOpenAI(model="gpt-4o")


async def run_agent(query):
  async with stdio_client(server_params) as (read, write):
    # Open an MCP session to interact with the math_server.py tool.
    async with ClientSession(read, write) as session:
      # Initialize the session.
      await session.initialize()
      # Load tools
      tools = await load_mcp_tools(session)
      # Create a ReAct agent.
      agent = create_react_agent(model, tools)
      # Run the agent.
      agent_response = await agent.ainvoke(
        # Now, let's give our message.
       {"messages": query})
      # Return the response.
      return agent_response["messages"][3].content
    
async def chat():
    print("Enter your question below, or type 'quit' to exit.")
    while True:
        try:
            query = input("\nYour query: ").strip()
            if query.lower() == 'quit':
                print("Session ended. Goodbye!")
                break
            print(f"Processing your request...")
            res = await run_agent(query)
            print("\nGemini's answer:")
            print(res)
        except KeyboardInterrupt:
            print("\nSession interrupted. Goodbye!")
            break
        except Exception as e:
            print(f"\nAn error occurred: {str(e)}")
    

if __name__ == "__main__":
    result = asyncio.run(chat())
    print(result)