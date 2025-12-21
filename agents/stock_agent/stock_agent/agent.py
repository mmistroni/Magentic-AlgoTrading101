from google.adk.agents import LlmAgent, SequentialAgent 
from vix_agent.vix_agents import INGESTION_TOOL_CALLER, INGESTION_MODEL_GENERATOR, \
                                FEATURE_TOOL_CALLER,  FEATURE_MODEL_GENERATOR, \
                                SIGNAL_TOOL_CALLER, SIGNAL_MODEL_GENERATOR


COT_WORKFLOW_PIPELINE = SequentialAgent(
    name="COTAnalysisWorkflow",
    sub_agents=[
        INGESTION_TOOL_CALLER,
        INGESTION_MODEL_GENERATOR,
        FEATURE_TOOL_CALLER,
        FEATURE_MODEL_GENERATOR,
        SIGNAL_TOOL_CALLER,
        SIGNAL_MODEL_GENERATOR
          # Assuming this is the final structured output
    ]
)

root_agent = COT_WORKFLOW_PIPELINE

# Execution Step
#initial_context = Context(market='Gold Futures') 
#final_context = root_agent.run(context=initial_context)
#final_result = final_context.get('final_output') 

