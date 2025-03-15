from langchain.chains import LLMChain
from langchain.agents import LLMSingleActionAgent
from langchain.tools import Tool
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import AgentOutputParser
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from magentic import prompt
from pydantic import BaseModel, Field
from typing import List
# Define prompt template (simplified)
from langchain.prompts import StringPromptTemplate
from langchain.schema import AgentAction, AgentFinish
from langchain.agents import AgentExecutor
from typing import List
from langchain.prompts import StringPromptTemplate
from langchain.tools import Tool
from openbb_functions import obb_tools, get_ticker_from_query
import os
import requests
import logging



# replace wtih fmp
# Define a tool
def search_api(query: str) -> str:
    return "Results for query"

def get_quote(query):

    ticker = get_ticker_from_query(query)
    logging.info('Querying for {ticker}')
    url = f"https://financialmodelingprep.com/api/v3/quote/{ticker}?apikey={os.environ['FMP_KEY']}"
    response = requests.get(url).json()
    logging.info(f'We got {response}')
    return response

search_tool = Tool(
    name="Search",
    func=search_api,
    description="Useful for answering questions",
)

quote_tool = Tool(
        name='Quote',
        func=get_quote,
        description="Useful for getting stock quote"
)

def get_tool_prompt(tools: List[Tool]) -> PromptTemplate:
    tool_descriptions = "\n".join([f"{tool.name}: {tool.description}" for tool in tools])
    return PromptTemplate(
        input_variables=["query"],
        template=f"""Given the following tools:

{tool_descriptions}

Which tool would be most appropriate to use for the following query: "{{query}}"?
Respond with just the name of the tool, nothing else.
"""
    )



@prompt(get_tool_prompt([search_tool, quote_tool] + obb_tools))
def select_tool(query: str) -> str:
    """Select the most appropriate tool based on the query."""
    pass

# Define a simple output parser (required for LLMSingleActionAgent)
class CustomOutputParser(AgentOutputParser):
    def parse(self, text: str) -> AgentAction | AgentFinish:
        if "Final Answer" in text:
            return AgentFinish(
                {"output": text.split("Final Answer:")[-1].strip()},
                text
            )
        else:
            # Extract tool name and input from LLM response
            tool_name = select_tool(text)
            tool_input = {"query": text.strip()}
            return AgentAction(tool=tool_name, tool_input=tool_input, log=text)
            


from typing import List
from langchain.prompts import StringPromptTemplate
from langchain.tools import Tool

from typing import List
from langchain.prompts import StringPromptTemplate
from langchain.tools import Tool

class CustomPromptTemplate(StringPromptTemplate):

    tools: list = []  

    def __init__(self, **kwargs):
        # Store tools as an attribute
        # Pass input variables to the parent class
        super().__init__(input_variables=["input", "agent_scratchpad"], **kwargs)
        self.tools = []
        

    def set_tools(self, tools):
        self.tools = tools
    
    def format(self, **kwargs) -> str:
        # Generate tool descriptions
        tool_descriptions = "\n".join([f"- {tool.name}: {tool.description}" for tool in self.tools])
        # Return the formatted prompt
        return f"""
        You are an intelligent financial assistant with access to the following tools:
        {tool_descriptions}

        When answering, decide if you need to use a tool based on the query. If you need stock quotes, use 'Quote'. For general searches, use 'Search'.

        Question: {kwargs['input']}
        Thought: {kwargs['agent_scratchpad']}
        """

tools = [search_tool, quote_tool] + obb_tools
llm = ChatOpenAI(temperature=0)
prompt = CustomPromptTemplate()#
prompt.set_tools(tools)
llm_chain = LLMChain(llm=llm, prompt=prompt)


agent = LLMSingleActionAgent(
    llm_chain=llm_chain,
    stop=["\nObservation:"],
    allowed_tools=[t.name for t in tools],
    output_parser=CustomOutputParser()  # Use default parser
)

agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=tools,  # Pass your actual tools here (e.g., [search_tool])
    verbose=True , # Optional: shows execution steps,
    max_iterations=3,
    early_stopping_method="force"

)
