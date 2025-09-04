import requests
# https://martinfowler.com/articles/function-call-LLM.html?utm_source=www.pythonweekly.com&utm_medium=newsletter&utm_campaign=python-weekly-issue-698-may-8-2025&_bhlid=f944725abe32d871b0b01da685a24e6396fdb57b
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