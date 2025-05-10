from openai import OpenAI
from .mcp_prompts import SYSTEM_PROMPT
from typing import List

class ShoppingAgent:
    def __init__(self):
        self.client = OpenAI()

    def run(self, user_message: str, conversation_history: List[dict] = None) -> str:
        if self.is_intent_malicious(user_message):
            return "Sorry! I cannot process this request."

        try:
            action = self.decide_next_action(user_message, conversation_history or [])
            return action.execute()
        except Exception as e:
            return f"Sorry, I encountered an error: {str(e)}"

    def decide_next_action(self, user_message: str, conversation_history: List[dict]):
        response = self.client.chat.completions.create(
            model="gpt-4-turbo-preview",
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                *conversation_history,
                {"role": "user", "content": user_message}
            ],
            tools=[
                {"type": "function", "function": SEARCH_SCHEMA},
                {"type": "function", "function": PRODUCT_DETAILS_SCHEMA},
                {"type": "function", "function": CLARIFY_SCHEMA}
            ]
        )
        
        tool_call = response.choices[0].message.tool_calls[0]
        function_args = eval(tool_call.function.arguments)
        
        if tool_call.function.name == "search_products":
            return Search(**function_args)
        elif tool_call.function.name == "get_product_details":
            return GetProductDetails(**function_args)
        elif tool_call.function.name == "clarify_request":
            return Clarify(**function_args)

    def is_intent_malicious(self, message: str) -> bool:
        pass
