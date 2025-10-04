from langchain_mcp_adapters import MCPTool
import await
import asyncio
# Replace with the actual URL of your MCP server
mcp_server_url = "http://localhost:8080"

try:
    # List the available tools on the MCP server
    available_tools = await MCPTool.list_tools(mcp_server_url)
    print("Available MCP Tools:", available_tools)

    if available_tools:
        # Choose a specific tool to load (replace 'your_tool_name' with an actual tool name)
        tool_name = "read_file"  # Example: Assuming a 'read_file' tool exists

        if tool_name in available_tools:
            mcp_tool = await MCPTool.from_tool_name(mcp_server_url, tool_name)
            print(f"Loaded MCP Tool: {mcp_tool.name}")

            # Now you can use this tool with a LangChain agent
            # For example, if you have an agent:
            # output = agent.run(f"Read the file named 'my_document.txt' using the {mcp_tool.name} tool.")
            # print(output)
        else:
            print(f"Tool '{tool_name}' not found on the MCP server.")
    else:
        print("No tools found on the MCP server.")

except Exception as e:
    print(f"Error connecting to MCP server: {e}")