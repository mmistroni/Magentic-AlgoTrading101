from langchain.chains import LLMChain
from langchain.agents import LLMSingleActionAgent
from langchain.tools import Tool
from langchain_community.chat_models import ChatOpenAI
from langchain.agents import AgentOutputParser
# Define prompt template (simplified)
from langchain.prompts import StringPromptTemplate
from langchain.schema import AgentAction, AgentFinish
from langchain.agents import AgentExecutor

# replace wtih fmp
# Define a tool
def search_api(query: str) -> str:
    return "Results for query"

search_tool = Tool(
    name="Search",
    func=search_api,
    description="Useful for answering questions",
)



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
            tool_name = "Search"  # Replace with your logic
            tool_input = {"query": text.strip()}
            return AgentAction(tool=tool_name, tool_input=tool_input, log=text)

class CustomPromptTemplate(StringPromptTemplate):
    def __init__(self, **kwargs):
        super().__init__(input_variables=["input", "agent_scratchpad"], **kwargs)

    def format(self, **kwargs) -> str:
        return f"""
        Answer this: {kwargs['input']}
        Thought: {kwargs['agent_scratchpad']}

"""# Initialize chain and agent
llm = ChatOpenAI(temperature=0)
prompt = CustomPromptTemplate()
llm_chain = LLMChain(llm=llm, prompt=prompt)

agent = LLMSingleActionAgent(
    llm_chain=llm_chain,
    stop=["\nObservation:"],
    allowed_tools=[search_tool.name],
    output_parser=CustomOutputParser()  # Use default parser
)

agent_executor = AgentExecutor.from_agent_and_tools(
    agent=agent,
    tools=[search_tool],  # Pass your actual tools here (e.g., [search_tool])
    verbose=True , # Optional: shows execution steps,
    max_iterations=5,
    early_stopping_method="force"

)
