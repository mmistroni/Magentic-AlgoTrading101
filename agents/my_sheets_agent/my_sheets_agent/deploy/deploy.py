import vertexai
from vertexai.preview import reasoning_engines
import os

# --- Configuration ---
PROJECT_ID = "datascience-projects"  # Replace with your Google Cloud Project ID
LOCATION = "us-central1"           # Replace with your desired GCP region (e.g., "us-central1", "europe-west4")
STAGING_BUCKET = "gs://your-adk-staging-bucket" # Replace with your GCS staging bucket
AGENT_NAME = "my-sheets-agent"  # A unique name for your deployed agent (Reasoning Engine resource)
AGENT_CODE_DIR = "my_sheets_agent"     # The directory containing your agent.py and requirements.txt

# --- Optional: Secret Manager Configuration ---
# If your agent uses secrets from Secret Manager, define them here.
# The keys here will be the environment variable names in your agent.
# The values are the full Secret Manager resource paths.
# Example: "projects/YOUR_PROJECT_ID/secrets/YOUR_SECRET_NAME/versions/latest"
SECRETS = {
    # "MY_API_KEY_ENV": f"projects/{PROJECT_ID}/secrets/my-api-key/versions/latest",
    # "DB_PASSWORD_ENV": f"projects/{PROJECT_ID}/secrets/database-password/versions/1"
}

# --- Initialize Vertex AI SDK ---
print(f"Initializing Vertex AI SDK for project: {PROJECT_ID}, location: {LOCATION}")
vertexai.init(
    project=PROJECT_ID,
    location=LOCATION,
    staging_bucket=STAGING_BUCKET,
)

# --- Load Your ADK Agent ---
# The ADK uses a convention where the 'agent' object is typically
# exposed at the top level of the module that is specified for the agent_code_dir.
# Ensure your agent_code_dir has an __init__.py and exposes your agent.
# For example, if your agent is defined as `my_agent` in `my_agent_app/agent.py`,
# and `my_agent_app/__init__.py` has `from .agent import my_agent`,
# you would generally point to `my_agent_app`.

try:
    # Dynamically import the agent from the specified directory
    import sys
    sys.path.insert(0, os.path.dirname(os.path.abspath(AGENT_CODE_DIR)))
    agent_module_name = os.path.basename(AGENT_CODE_DIR)
    agent_module = __import__(agent_module_name)

    # Assuming your agent is wrapped in an AdkApp instance named 'app'
    # within your agent_module (e.g., in my_agent_app/__init__.py or my_agent_app/agent.py)
    # Adjust this line based on how your AdkApp instance is exposed.
    # A common pattern is to have `app = reasoning_engines.AdkApp(agent=your_agent)`
    # directly in your main agent file or its __init__.py.
    if hasattr(agent_module, 'app'):
        local_adk_app = agent_module.app
        print(f"Successfully loaded ADK app from {AGENT_CODE_DIR}.")
    else:
        # Fallback if 'app' is not directly exposed, try to find an Agent object and wrap it
        # This is less common for direct deployment, but useful if you only expose the raw Agent
        found_agent = None
        for attr_name in dir(agent_module):
            attr = getattr(agent_module, attr_name)
            if isinstance(attr, (reasoning_engines.Agent, reasoning_engines.LlmAgent)): # Add other BaseAgent types if relevant
                found_agent = attr
                break
        if found_agent:
            local_adk_app = reasoning_engines.AdkApp(agent=found_agent, enable_tracing=True)
            print(f"Wrapped found agent '{found_agent.name}' into an AdkApp.")
        else:
            raise AttributeError(f"Could not find an 'app' instance or a suitable 'Agent' object in {AGENT_CODE_DIR}. "
                                 "Ensure your agent is wrapped in `vertexai.preview.reasoning_engines.AdkApp()` "
                                 "and exposed in your agent's main module or its `__init__.py`.")

except Exception as e:
    print(f"Error loading local agent from {AGENT_CODE_DIR}: {e}")
    print("Please ensure your agent code adheres to the ADK structure, "
          "especially how the `AdkApp` instance is exposed.")
    sys.exit(1)


# --- Define Requirements ---
# This is crucial for your agent's dependencies on the deployed environment.
# It should match the requirements.txt you used for local development.
# ADK usually handles internal dependencies, but specific framework dependencies
# (like langchain, pydantic, cloudpickle) are often needed.
requirements = [
    "google-cloud-aiplatform[adk,agent_engines]",
    # Add any other specific requirements your agent needs
    # e.g., "langchain", "requests", "beautifulsoup4"
    # It's highly recommended to sync this with your local requirements.txt
    # and pin versions for stability (e.g., "langchain==0.1.0").
]

# You can also use `extra_packages` for local files/directories or wheel files
# For example, if your agent code itself relies on other local Python files
# within the `AGENT_CODE_DIR` that aren't part of a pip-installable package,
# you might include `extra_packages=[AGENT_CODE_DIR]`.
# For simplicity, we're assuming the agent_code_dir itself is packaged.

# --- Prepare Secret Environment Variables ---
secret_env_vars = []
for env_name, secret_path in SECRETS.items():
    secret_env_vars.append(
        reasoning_engines.ReasoningEngine.SecretEnv(
            env_var_name=env_name,
            secret_version=secret_path
        )
    )

# --- Deploy the Agent ---
print(f"\nAttempting to deploy agent '{AGENT_NAME}'...")
try:
    remote_agent = reasoning_engines.create(
        display_name=AGENT_NAME,
        app=local_adk_app, # The AdkApp instance you loaded
        requirements=requirements,
        # Uncomment and configure if you have other environment variables
        # environment_variables={"MY_OTHER_ENV_VAR": "some_value"},
        secret_env=secret_env_vars if secret_env_vars else None,
        # For more options, refer to the Vertex AI Agent Engine documentation
        # https://cloud.google.com/vertex-ai/generative-ai/docs/agent-engine/deploy
    )

    print(f"\nAgent '{AGENT_NAME}' deployment initiated successfully!")
    print(f"Resource name: {remote_agent.resource_name}")
    print(f"To monitor deployment status, visit: ")
    print(f"https://console.cloud.google.com/vertex-ai/reasoning-engines/details/{remote_agent.resource_name.split('/')[-1]}?project={PROJECT_ID}&region={LOCATION}")
    print("\nDeployment can take several minutes. You can query the agent once it's ready.")

    # Optional: Wait for deployment to complete and test
    # print("\nWaiting for agent to be ready (this may take a few minutes)...")
    # remote_agent.wait_until_ready()
    # print("Agent is ready!")

    # # Example: Test the deployed agent (uncomment to enable)
    # print("\nTesting deployed agent...")
    # response = remote_agent.query(input="Hello, tell me about the weather in London.")
    # print(f"Agent response: {response.output}")

except Exception as e:
    print(f"\nError deploying agent: {e}")
    print("Please check your configuration, IAM permissions, and agent code.")