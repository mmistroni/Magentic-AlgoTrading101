from langchain.agents import AgentExecutor, LLMSingleActionAgent
from langchain.prompts import StringPromptTemplate
from langchain_community.chat_models import ChatOpenAI
from langchain.memory import ConversationBufferMemory
from langchain.chains import LLMChain
from openbb_functions import tools
from typing import List  # For type hinting (optional, but good practice)
from langchain.tools import Tool

# Your existing LLM setup
llm = ChatOpenAI(temperature=0)
memory = ConversationBufferMemory(return_messages=True)


# Update your prompt template to include the new tools
class CustomPromptTemplate(StringPromptTemplate):
    template: str
    tools: List[Tool]

    def format(self, **kwargs) -> str:
        intermediate_steps = kwargs.pop("intermediate_steps")
        thoughts = ""
        for action, observation in intermediate_steps:
            thoughts += f"Action: {action.tool}\nAction Input: {action.tool_input}\nObservation: {observation}\nThought: "
        kwargs["agent_scratchpad"] = thoughts
        kwargs["tools"] = "\n".join([f"{tool.name}: {tool.description}" for tool in self.tools])
        kwargs["tool_names"] = ", ".join([tool.name for tool in self.tools])
        return self.template.format(**kwargs)


prompt = CustomPromptTemplate(
    template="""You are a financial assistant with access to tools. Answer the following question:

{input}

Available tools:
{tools}

Use the following format:

Question: the input question you must answer
Thought: you should always think about what to do
Action: the action to take, should be one of [{tool_names}]
Action Input: the input to the action
Observation: the result of the action
... (this Thought/Action/Action Input/Observation can repeat N times)
Thought: I now know the final answer
Final Answer: the final answer to the original input question

{agent_scratchpad}""",
    tools=tools,
    input_variables=["input", "intermediate_steps"]
)

# LLMChain and Agent setup
llm_chain = LLMChain(llm=llm, prompt=prompt)
agent = LLMSingleActionAgent(
    llm_chain=llm_chain,
    output_parser=None,
    stop=["\nObservation:"],
    allowed_tools=[tool.name for tool in tools]
)
agent_executor = AgentExecutor.from_agent_and_tools(agent=agent, tools=tools, verbose=True)