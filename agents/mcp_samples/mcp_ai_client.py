import asyncio
import json
import sys
from mcp.client.http import http_client_streamable
from mcp import ClientSession

# --- Configuration ---
SERVER_URL = "http://localhost:7001"
# ---------------------

# A global list to store the tools after discovery
AVAILABLE_TOOLS = {}

async def inspect_server(session: ClientSession):
    """Connects to the server, initializes the session, and lists all available tools."""
    print(f"🔗 Connecting to MCP server at: {SERVER_URL}...")
    
    # 1. Initialize the session to establish the connection and exchange basic info
    try:
        await session.initialize()
        print("✅ Session initialized successfully.")
    except Exception as e:
        print(f"❌ Failed to initialize session: {e}")
        return False

    # 2. Discover available tools
    try:
        tools = await session.list_tools()
        print(f"\n🔬 Found {len(tools)} exposed tools:")
        
        # Display and store tool information
        global AVAILABLE_TOOLS
        AVAILABLE_TOOLS = {}
        for tool in tools:
            name = tool.get('name')
            description = tool.get('description', 'No description provided.')
            input_schema = tool.get('input_schema', {})
            
            AVAILABLE_TOOLS[name] = {
                "description": description,
                "input_schema": input_schema
            }
            
            print(f"--- Tool: \033[1m{name}\033[0m ---")
            print(f"  Description: {description}")
            
            if 'properties' in input_schema.get('schema', {}):
                props = input_schema['schema']['properties']
                required = input_schema['schema'].get('required', [])
                
                print("  Arguments:")
                for prop_name, prop_data in props.items():
                    req_marker = " (Required)" if prop_name in required else ""
                    prop_type = prop_data.get('type', 'any')
                    print(f"    - \033[36m{prop_name}\033[0m (\033[33m{prop_type}\033[0m){req_marker}: {prop_data.get('description', '')}")
            else:
                print("  Arguments: None")

        return True

    except Exception as e:
        print(f"❌ Failed to list tools: {e}")
        return False

async def interactive_loop(session: ClientSession):
    """Runs the main interactive loop to accept tool calls from the user."""
    while True:
        try:
            # Use raw input for interactive terminal use
            user_input = await asyncio.to_thread(input, "\n\033[92mEnter tool call (e.g., tool_name '{\"arg1\": 123}'):\033[0m ").strip()
            
            if not user_input:
                continue

            if user_input.lower() in ['exit', 'quit']:
                print("👋 Exiting client.")
                break
            
            if user_input.lower() in ['tools', 'list']:
                # Re-run discovery for convenience
                await inspect_server(session)
                continue

            try:
                # Basic parsing: split tool name from arguments (first space)
                parts = user_input.split(' ', 1)
                tool_name = parts[0]
                args_str = parts[1].strip() if len(parts) > 1 else "{}"
                
                # Parse arguments as JSON
                arguments = json.loads(args_str)

            except (IndexError, json.JSONDecodeError) as e:
                print(f"🛑 Invalid input format or JSON error. Usage: \033[1mtool_name '{{\"arg1\": \"value\"}}'\033[0m")
                print(f"    Error: {e}")
                continue

            if tool_name not in AVAILABLE_TOOLS:
                print(f"🛑 Error: Tool '\033[1m{tool_name}\033[0m' is not available. Type 'tools' to see the list.")
                continue

            print(f"🚀 Calling tool '\033[1m{tool_name}\033[0m' with arguments: {arguments}")
            
            # 3. Call the exposed tool
            tool_call_result = await session.call_tool(tool_name, arguments)
            
            print("\n✨ \033[95mTool Result\033[0m:")
            print(json.dumps(tool_call_result, indent=2))
            
        except EOFError:
            print("👋 Detected EOF (Ctrl+D), exiting.")
            break
        except Exception as e:
            print(f"❌ An unexpected error occurred during tool call: {e}")

async def main():
    """Main function to set up the client and run the interactive loop."""
    
    # Use http_client_streamable to connect to the remote server URL
    # This function returns the read/write callables needed for ClientSession
    try:
        read, write = http_client_streamable(SERVER_URL)
    except Exception as e:
        print(f"❌ Could not create HTTP client for {SERVER_URL}. Is your server running and accessible?")
        print(f"Error: {e}")
        sys.exit(1)

    # Use AsyncExitStack for robust session management (cleanup)
    async with ClientSession(read, write) as session:
        if await inspect_server(session):
            await interactive_loop(session)

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n👋 Client stopped by user (Ctrl+C).")
    except Exception as e:
        print(f"\n\n🚨 Program error: {e}")