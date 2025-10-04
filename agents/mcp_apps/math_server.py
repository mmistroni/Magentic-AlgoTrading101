#https://tirendazacademy.medium.com/mcp-with-langchain-cabd6199e0ac

# Build an MCP server
from mcp.server.fastmcp import FastMCP 

# Initialize the class
mcp = FastMCP("Math")

@mcp.tool()
def add(a: int, b: int) -> int:
  ''' Adds two numbers together.'''
  return a + b

@mcp.tool()
def subtract(a: int, b: int) -> int:
  ''' Subtracts b from a.'''
  return a - b

@mcp.tool()
def multiply(a: int, b: int) -> int:
  ''' Multiplies two numbers.'''
  return a * b


if __name__ =="__main__":
    mcp.run(transport="stdio")