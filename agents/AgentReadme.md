# Agent workbook

1. Google Sheets Agent  DONE - July 2025
2. Google MultiAgent - following ADK agent team samples i
3. Google News Agent - Read list of shares from GCP and fetch news - see samples https://medium.com/@airabbitX/turn-claude-into-a-super-power-with-mcp-activepieces-f76cc83049fc
4. Google Expenditure Agent - replacing JavaScript UI to update expenses in Amazon DB
5. Google OBB Agent for Six step dance stock investigation
        - obb
        - adk
        
6. implements same agents using 
          - langchain
          - langgraph
          - crewai
          - smolagent



# MCP tutorial - DONE = Zoo Agent
https://codelabs.developers.google.com/codelabs/cloud-run/use-mcp-server-on-cloud-run-with-an-adk-agent?hl=en&utm_source=email&utm_medium=newsletter&utm_campaign=dev_program_september#0 

The tutorial above deploys an agent which interacts wtih an mcp server

## Now we need to call the agent above programmatically


# MultiAgent tutorial https://cloud.google.com/blog/products/ai-machine-learning/build-multi-agentic-systems-using-google-adk - DONE

## Now we need to call the agent above programmatically
  

#Once we sort out the deployment and programmatic call, we'll need to draft a set of steps we can apply
#for all the agents




## Agent Chat UI
Tutorials and Resources for Agent Chat UI
Official Documentation and Quickstart Guide: The LangChain documentation for Agent Chat UI is the best place to start. It provides a quickstart guide for both a hosted version and local development. It explains how to run the UI, connect it to your LangGraph agent (by providing the deployment URL and graph ID), and how to configure it.

Agent Chat UI Documentation: https://docs.langchain.com/oss/python/langchain-ui

Live Demo: https://agentchat.vercel.app/

Video Tutorials: There are several video tutorials that walk you through the setup and usage of Agent Chat UI.

Introducing Agent Chat UI: https://www.youtube.com/watch?v=lInrwVnZ83o

Create a Simple Web-based Chat UI for LangGraph Agents: https://www.youtube.com/watch?v=SMuOVOG-cjA

How I interact with my LangGraph AI Agent using Agent Chat: https://www.youtube.com/watch?v=KKypXqaMqrU

Code Examples: The source code for the Agent Chat UI is available on GitHub. This is the best place to find sample code for the frontend and learn how it interacts with the agent backend.

Agent Chat UI GitHub Repository: https://github.com/langchain-ai/agent-chat-ui

These resources should provide a complete picture of how to deploy and integrate the Agent Chat UI with your own agent.

# Multi Agent 
https://www.youtube.com/watch?v=tl5rQktClqc        


# MCP
https://langchain-ai.github.io/langgraph/agents/mcp/an



# anothe rsample
https://innovationlab.fetch.ai/resources/docs/next/examples/mcp-integration/langgraph-mcp-agent-example


######### deployig agent on glcoud

uvx --from google-adk adk deploy cloud_run \
    --project=datascience-projects \
    --region=europe-west1 \
    --service_name=zoo-data-backend . \
    --allow-unauthenticated=false  # <--- This is the key flag for a protected service


### create iam service..


## add iam service
gcloud run services add-iam-policy-binding zoo-data-backend \
    --member='' \
    --role='roles/run.invoker' \
    --region='europe-west1' \
    --project=datascience-projects

### curl call
# 1. Get the URL of your deployed Cloud Run service
export APP_URL="https://your-agent-service-xxxx-uc.a.run.app"

# 2. Get an identity token (if your service requires authentication)
export TOKEN=$(gcloud auth print-identity-token)

curl -X POST "$APP_URL/run_sse" \
-H "Authorization: Bearer $TOKEN" \
-H "Content-Type: application/json" \
-d '{
  "app_name": "your_agent_directory_name",
  "user_id": "api_user",
  "session_id": "api_session_123",
  "new_message": {
    "role": "user",
    "parts": [
      {
        "text": "What is the capital of Germany?"
      }
    ]
  },
  "streaming": false
}'

##  Agent on Cloud Run - we use this to figure out what are we missing from mcp zoo samples
https://google.github.io/adk-docs/deploy/cloud-run/
https://google.github.io/adk-docs/deploy/cloud-run/

