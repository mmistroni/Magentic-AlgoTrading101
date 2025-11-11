from .prompts import CAPITAL_AGENT_INSTRUCTION
from .tools import get_capital_city
from google.adk.agents import LlmAgent, SequentialAgent, Context    
from vix_agent.vix_agents import INGESTION_AGENT, FEATURE_AGENT, SIGNAL_AGENT



initial_context = Context(market='Gold Futures') 

root_agent = SequentialAgent(
    name="COTAnalysisWorkflow",
    sub_agents=[
        INGESTION_AGENT,      # Retrieves data and writes 'raw_market_data' to Context.
        FEATURE_AGENT,        # Reads 'raw_market_data', calculates, writes 'engineered_features' to Context.
        SIGNAL_AGENT          # Reads 'engineered_features', outputs final SignalDataModel.
    ]
)

# Execution Step
final_context = root_agent.run(context=initial_context)
final_result = final_context.get('final_output') 

