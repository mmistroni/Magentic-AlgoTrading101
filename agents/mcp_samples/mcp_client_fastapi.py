import socket
import json
from typing import List, Any
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
import os

# --- Configuration for the *external* MCP Server (mcp_server.py) ---
MCP_SERVER_HOST = '127.0.0.1'
MCP_SERVER_PORT = 55555

# --- Pydantic Models for FastAPI Request/Response Validation ---

class ToolCallRequest(BaseModel):
    """
    Defines the structure for the HTTP POST request body.
    This structure is then translated into the socket-based MCP format.
    """
    tool_name: str
    arguments: List[Any]

class ToolCallResponse(BaseModel):
    """
    Defines the expected structure of the response returned by this FastAPI client.
    """
    tool_name: str
    status: str
    output: Any
    
# --- FastAPI App Initialization ---
app = FastAPI(
    title="MCP Proxy Agent API",
    description="A FastAPI server that translates HTTP requests into Model Context Protocol (MCP) socket calls.",
    version="1.0.0"
)

def call_mcp_server(tool_name: str, arguments: List[Any]):
    """
    Establishes a socket connection, sends the MCP request, and receives the response.
    
    Args:
        tool_name: The name of the tool to call (e.g., 'add').
        arguments: List of arguments for the tool.
        
    Returns:
        A dictionary containing the parsed MCP server response.
    """
    
    # 1. Construct the MCP Tool Call JSON (the payload expected by mcp_server.py)
    mcp_request = {
        "type": "tool_call",
        "tool_name": tool_name.lower(),
        "arguments": arguments
    }
    
    request_json = json.dumps(mcp_request)
    
    # 2. Establish and send via socket
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.connect((MCP_SERVER_HOST, MCP_SERVER_PORT))
        print(f"Proxy connected and sending request for tool: {tool_name}")
        
        # Send the JSON request, followed by a newline for clear demarcation
        s.sendall(request_json.encode('utf-8') + b'\n')
        
        # 3. Receive the response
        response_data = s.recv(4096).decode('utf-8').strip()
        
        # 4. Parse and return
        mcp_response = json.loads(response_data)
        return mcp_response
        
    except ConnectionRefusedError:
        raise HTTPException(
            status_code=503, 
            detail=f"Connection refused to MCP Server at {MCP_SERVER_HOST}:{MCP_SERVER_PORT}. Is mcp_server.py running?"
        )
    except json.JSONDecodeError:
        raise HTTPException(
            status_code=500,
            detail="Received malformed JSON response from MCP Server."
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"An unexpected socket error occurred: {str(e)}")
    finally:
        s.close()


@app.post("/call_tool", response_model=ToolCallResponse)
def call_tool(request_body: ToolCallRequest):
    """
    Endpoint to call a tool on the external MCP server.
    
    Example body:
    {
      "tool_name": "add",
      "arguments": [5, 10, 2]
    }
    """
    
    # Call the external MCP server via socket
    mcp_result = call_mcp_server(request_body.tool_name, request_body.arguments)
    
    # Ensure the result matches the expected MCP response structure
    if mcp_result.get("type") == "tool_result":
        return ToolCallResponse(
            tool_name=mcp_result.get("tool_name", request_body.tool_name),
            status=mcp_result.get("status", "unknown"),
            output=mcp_result.get("output", "No output provided")
        )
    elif mcp_result.get("type") == "error":
        raise HTTPException(
            status_code=400,
            detail=f"MCP Server Error: {mcp_result.get('message', 'Unknown Error')}"
        )
    else:
        raise HTTPException(
            status_code=500,
            detail="Received unexpected response format from MCP Server."
        )


# --- Entry Point (Requires uvicorn to run) ---
if __name__ == "__main__":
    # Note: When running in a Codespace/container, use 0.0.0.0 for the host 
    # to make it accessible externally, and specify a port (e.g., 8000).
    # You must install 'fastapi' and 'uvicorn[standard]' first: pip install fastapi uvicorn[standard]
    print("--- Starting FastAPI MCP Proxy Server ---")
    print(f"Ensure mcp_server.py is running on {MCP_SERVER_HOST}:{MCP_SERVER_PORT}!")
    
    # Run Uvicorn on port 8000
    uvicorn.run(app, host="0.0.0.0", port=8000)
