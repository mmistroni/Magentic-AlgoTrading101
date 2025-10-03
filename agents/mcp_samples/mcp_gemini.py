import socket
import threading
import json
import sys

# --- Configuration ---
HOST = '127.0.0.1'
PORT = 55555

# Define the "Tools" available on this server
AVAILABLE_TOOLS = {
    "add": lambda args: sum(args),
    "subtract": lambda args: args[0] - sum(args[1:]),
    "echo": lambda args: " ".join(map(str, args))
}

def execute_tool(tool_name, arguments):
    """Executes a defined tool and returns a result or error."""
    try:
        if tool_name not in AVAILABLE_TOOLS:
            return {"error": f"Tool '{tool_name}' not found on this server."}
        
        # Convert arguments to numbers for math operations if necessary
        if tool_name in ["add", "subtract"]:
            try:
                numeric_args = [int(arg) for arg in arguments]
            except ValueError:
                return {"error": f"Tool '{tool_name}' requires numeric arguments."}
            result = AVAILABLE_TOOLS[tool_name](numeric_args)
        else:
            # For tools like 'echo', pass arguments as is
            result = AVAILABLE_TOOLS[tool_name](arguments)

        return {"result": result}
    
    except Exception as e:
        return {"error": f"Execution failed for tool '{tool_name}': {str(e)}"}

def handle_client(conn, addr):
    """Handles communication with a single MCP client (agent)."""
    client_address_str = f"{addr[0]}:{addr[1]}"
    print(f"Server: Connection established with Agent {client_address_str}")

    while True:
        try:
            # 1. Receive data (expecting a structured JSON payload)
            data = conn.recv(1024)
            if not data:
                break
            
            # 2. Decode and Parse the JSON message
            raw_message = data.decode('utf-8').strip()
            print(f"\n[Agent {addr[1]} REQUEST]: {raw_message}")
            
            try:
                request = json.loads(raw_message)
            except json.JSONDecodeError:
                response = {"type": "error", "message": "Invalid JSON format received."}
                conn.sendall(json.dumps(response).encode('utf-8'))
                continue

            # 3. Process the Tool Call Request
            if request.get("type") == "tool_call":
                tool_name = request.get("tool_name", "").lower()
                arguments = request.get("arguments", [])
                
                tool_result = execute_tool(tool_name, arguments)
                
                # 4. Construct the MCP Tool Result Response
                response_payload = {
                    "type": "tool_result",
                    "tool_name": tool_name,
                    "status": "success" if "result" in tool_result else "failure",
                    "output": tool_result.get("result", tool_result.get("error"))
                }
            else:
                response_payload = {"type": "error", "message": "Unknown or malformed request type."}

            # 5. Send the JSON response back to the client
            response_json = json.dumps(response_payload, indent=2)
            print(f"[Agent {addr[1]} RESPONSE]: Sending result.")
            conn.sendall(response_json.encode('utf-8') + b'\n')

        except ConnectionResetError:
            break
        except Exception as e:
            print(f"Error handling agent {client_address_str}: {e}")
            break

    print(f"Server: Connection closed with Agent {client_address_str}")
    conn.close()

def start_server():
    """Initializes and runs the main server loop."""
    server_socket = None
    try:
        server_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        server_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        server_socket.bind((HOST, PORT))
        server_socket.listen(5)
        
        print(f"*** Minimal MCP Server running on {HOST}:{PORT} ***")
        print(f"Available Tools: {list(AVAILABLE_TOOLS.keys())}")
        print("Waiting for client agents...")
        
        while True:
            conn, addr = server_socket.accept()
            # Start a new thread for each connecting agent
            client_thread = threading.Thread(target=handle_client, args=(conn, addr))
            client_thread.daemon = True
            client_thread.start()

    except Exception as e:
        print(f"Server error: {e}")
    finally:
        if server_socket:
            server_socket.close()

if __name__ == '__main__':
    start_server()
