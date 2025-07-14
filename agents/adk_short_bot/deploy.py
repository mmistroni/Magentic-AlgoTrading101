import os
from vertexai import agent_engines
from vertexai.preview import reasoning_engines
import vertexai

def main():
    # 1. Set your Google Cloud project details
    PROJECT_ID = "datascience-projects"
    LOCATION = "us-central1"  # e.g., "us-central1"
    STAGING_BUCKET = "gs://adk_short_bot"

    # 2. Initialize Vertex AI
    vertexai.init(
        project=PROJECT_ID,
        location=LOCATION,
        staging_bucket=STAGING_BUCKET
    )

    # 3. Import your root agent using absolute import
    from adk_short_bot.agent import root_agent

    # 4. Create an ADK app with tracing enabled
    app_instance = reasoning_engines.AdkApp(
        agent=root_agent,
        enable_tracing=True
    )

    # 5. Deploy the agent to Agent Engine
    remote_agent = agent_engines.create(
        app_instance,
        requirements=["google-cloud-aiplatform[adk,agent_engines]"],  # minimal requirement
        extra_packages=[os.path.join(os.path.dirname(__file__), "adk_short_bot")],  # include your agent package
        # env_vars={},  # add if you need environment variables
    )

    print("Agent deployed successfully!")
    print("Resource name:", remote_agent.resource_name)

if __name__ == "__main__":
    main()
