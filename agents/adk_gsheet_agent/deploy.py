import os
import yaml
from datetime import datetime
from vertexai import agent_engines
from vertexai.preview import reasoning_engines

def load_root_agent():
    import sys
    agent_dir = os.path.join(os.path.dirname(__file__), "adk_gsheet_agent")
    if agent_dir not in sys.path:
        sys.path.insert(0, agent_dir)
    from agent import root_agent  # Adjust if your agent is named differently
    return root_agent

def main():
    # 1. Load environment variables from config.yaml
    env_vars = {}
    config_path = os.path.join(os.path.dirname(__file__), "adk_gsheet_agent", "config.yaml")
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            config = yaml.safe_load(f)
            env_vars = {
                "SPREADSHEET_ID_SECRET_ID": config.get("spreadsheet_id_secret_id"),
                "SERVICE_ACCOUNT_CREDS_SECRET_ID": config.get("service_account_creds_secret_id"),
                "DEFAULT_SHEET_NAME": config.get("default_sheet_name", "Sheet1"),
                "DEFAULT_START_EXPENSE_ROW": str(config.get("default_start_expense_row", 7)),
            }

    # 2. Load requirements from requirements.txt
    requirements_path = os.path.join(os.path.dirname(__file__), "adk_gsheet_agent", "requirements.txt")
    with open(requirements_path, "r") as f:
        requirements = [line.strip() for line in f if line.strip() and not line.startswith("#")]

    # 3. Set up Vertex AI project info
    PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "datascience-projects")
    LOCATION = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
    STAGING_BUCKET = os.environ.get("STAGING_BUCKET", "gs://adk_short_bot")

    import vertexai
    vertexai.init(project=PROJECT_ID, location=LOCATION, staging_bucket=STAGING_BUCKET)

    # 4. Instantiate AdkApp with the agent
    root_agent = load_root_agent()
    app_instance = reasoning_engines.AdkApp(agent=root_agent, enable_tracing=True)

    # 5. Deploy to Agent Engine (NO resource_id, NO agent_builder)
    print(f"[{datetime.now()}] Creating Agent Engine deployment...")
    try:
        remote_agent = agent_engines.create(
            app_instance,
            requirements=requirements,
            extra_packages=[os.path.join(os.path.dirname(__file__), "adk_gsheet_agent")],
            env_vars=env_vars,
            # runtime_service_account=agent_runtime_service_account_email,  # Uncomment and set if needed
            # staging_bucket=STAGING_BUCKET,  # Uncomment if you need to specify
        )
        print(f"[{datetime.now()}] Agent deployment successful! Agent Name: {remote_agent.name}")
        print(f"Agent Console URL: https://console.cloud.google.com/vertex-ai/agents/detail/{remote_agent.name.split('/')[-1]}?project={PROJECT_ID}&region={LOCATION}")
    except Exception as e:
        print(f"CRITICAL ERROR: [{datetime.now()}] Agent deployment failed: {e}")
        import traceback
        traceback.print_exc()
        raise

if __name__ == "__main__":
    main()
