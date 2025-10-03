import requests
#  
class MCPClient:
    def __init__(self, base_url):
        self.base_url = base_url.rstrip("/")

    def get_tools(self):
        response = requests.get(f"{self.base_url}/tools")
        response.raise_for_status()
        return response.json()

    def invoke(self, tool_name, arguments):
        url = f"{self.base_url}/invoke/{tool_name}"
        response = requests.post(url, json=arguments)
        response.raise_for_status()
        return response.json()