#https://tirendazacademy.medium.com/mcp-with-langchain-cabd6199e0ac
from mcp.server.fastmcp import FastMCP 
# Removed: asyncio, WikipediaQueryRun, WikipediaAPIWrapper (as they are not used for the placeholder)

# Initialize the FastMCP server
mcp = FastMCP("MathAndKnowledge")

# ------------------------------------------------
# 1. Global Tool Initialization (Removed for placeholder test)
# ------------------------------------------------


# ------------------------------------------------
# 2. Math Tools (Simple Functions)
# ------------------------------------------------

@mcp.tool()
def add(a: int, b: int) -> int:
    '''Adds two numbers together.'''
    return a + b

@mcp.tool()
def subtract(a: int, b: int) -> int:
    '''Subtracts b from a.'''
    return a - b

@mcp.tool()
def multiply(a: int, b: int) -> int:
    '''Multiplies two numbers.'''
    return a * b

@mcp.tool()
def divide(a: int, b: int) -> int:
    '''Divides a by b. Raises error if b is zero.'''
    return a / b

@mcp.tool()
def power(a: int, b: int) -> int:
    '''a raised to the power of b.'''
    return a**b


# ------------------------------------------------
# 3. Wikipedia Tool (Placeholder for Tool Selection Test)
# ------------------------------------------------

@mcp.tool()
def query_wikipedia(query: str) -> str:
    '''
    REQUIRED TOOL: Use this tool for ALL general knowledge, factual questions, 
    and queries that are NOT mathematical calculations (add, subtract, etc.).
    If the question is not a pure math problem, you MUST use this tool to find the answer.
    Returns a confirmation string for debugging.
    '''
    # This is the placeholder response. If the agent/server returns this string, 
    # the tool selection and routing is working correctly for non-math queries.
    return 'Tool Selected Successfully: You should query wikipedia for this'

if __name__ =="__main__":
    # The FastMCP server is now ready to run and expose both sets of tools
    mcp.run(transport="stdio")
