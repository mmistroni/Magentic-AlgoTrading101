import socket
import threading
import json
import sys
import time

# --- Configuration ---
HOST = '127.0.0.1'
PORT = 55555

def receive_messages(client_socket):
    """Continuously receives and displays structured responses from the server."""
    while True:
        try:
            data = client_socket.recv(4096)
            if data:
                # Clear the current input line
                sys.stdout.write('\r' + ' ' * 80 + '\r') 
                
                # Process incoming JSON response
                response_json = data.decode('utf-8').strip()
                try:
                    response = json.loads(response_json)
                    
                    if response.get("type") == "tool_result":
                        print("-" * 50)
                        print(f"TOOL RESULT: {response['tool_name'].upper()}")
                        print(f"STATUS: {response['status'].upper()}")
                        print(f"OUTPUT: {response['output']}")
                        print("-" * 50)
                    else:
                        print(f"[SERVER RAW MESSAGE]: {response_json}")
                        
                except json.JSONDecodeError:
                    print(f"[ERROR PARSING SERVER RESPONSE]: {response_json}")
                
                # Re-display the prompt
                sys.stdout.write('AGENT> ')
                sys.stdout.flush()
            else:
                print("\n[Server disconnected. Press Enter to exit.]")
                client_socket.close()
                break
        except OSError:
            # Socket closed
            break
        except Exception as e:
            print(f"\n[An error occurred in receiver: {e}. Disconnecting.]")
            client_socket.close()
            break

def start_client():
    """Handles user input, translates it to MCP JSON, and sends it."""
    client_socket = None
    try:
        client_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        print(f"AGENT: Attempting to connect to MCP Server at {HOST}:{PORT}...")
        client_socket.connect((HOST, PORT))
        print("AGENT: Connected! Use the 'CALL' command to invoke a tool.")
        print("Example: CALL add 10 20 5")
        print("Type 'quit' or 'exit' to disconnect.")

        # Start listening thread
        receive_thread = threading.Thread(target=receive_messages, args=(client_socket,))
        receive_thread.daemon = True
        receive_thread.start()

        # Input loop
        while True:
            user_input = input('AGENT> ').strip()
            
            if user_input.lower() in ('quit', 'exit'):
                break

            # Process command: expecting "CALL [tool_name] [arg1] [arg2]..."
            parts = user_input.split()
            if not parts or parts[0].upper() != 'CALL':
                print("Invalid command. Use format: CALL <tool_name> <arg1> <arg2>...")
                continue
            
            tool_name = parts[1].lower()
            arguments = parts[2:]
            
            # Construct the MCP Tool Call JSON
            mcp_request = {
                "type": "tool_call",
                "tool_name": tool_name,
                "arguments": arguments
            }
            
            # Send the JSON request
            request_json = json.dumps(mcp_request)
            client_socket.sendall(request_json.encode('utf-8'))

    except ConnectionRefusedError:
        print(f"\nAGENT: Error: Connection refused. Is the server running on {HOST}:{PORT}?")
    except Exception as e:
        print(f"\nAGENT: Client error: {e}")
    finally:
        if client_socket:
            print("AGENT: Disconnecting...")
            client_socket.close()

if __name__ == '__main__':
    start_client()
