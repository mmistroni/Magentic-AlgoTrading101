import os
import sys

import vertexai
from absl import app, flags
from dotenv import load_dotenv
from vertexai import agent_engines
from vertexai.preview import reasoning_engines

# --- No direct import of the agent object here. ---
# The agent will be loaded dynamically via AGENT_ENTRYPOINT.

FLAGS = flags.FLAGS
flags.DEFINE_string("project_id", None, "GCP project ID.")
flags.DEFINE_string("location", None, "GCP location.")
flags.DEFINE_string("bucket", None, "GCP bucket for staging resources.")
flags.DEFINE_string(
    "agent_name", "adk-gsheet-agent", "Name for the deployed Agent Engine resource."
)
flags.DEFINE_string("user_id", "test_user", "User ID for session operations.")
flags.DEFINE_string("session_id", None, "Session ID for operations.")
flags.DEFINE_bool("create", False, "Creates a new deployment.")
flags.DEFINE_bool("delete", False, "Deletes an existing deployment.")
flags.DEFINE_bool("list", False, "Lists all deployments.")
flags.DEFINE_bool("create_session", False, "Creates a new session.")
flags.DEFINE_bool("list_sessions", False, "Lists all sessions for a user.")
flags.DEFINE_bool("get_session", False, "Gets a specific session.")
flags.DEFINE_bool("send", False, "Sends a message to the deployed agent.")
flags.DEFINE_string(
    "message",
    "Can you provide me with the total expenses from Sheet1?",
    "Message to send to the agent.",
)
flags.mark_bool_flags_as_mutual_exclusive(
    [
        "create",
        "delete",
        "list",
        "create_session",
        "list_sessions",
        "get_session",
        "send",
    ]
)

# --- Agent Specifics for Deployment ---
# This path points to the directory containing your agent's 'agent.py' and 'config.yaml'.
# It must be relative to where deploy_agent.py is run (your project root).
AGENT_SOURCE_DIR = "./adk_gsheet_agent"

# This is the fully qualified path to the function within your agent's package
# that Agent Engine will call to instantiate your agent.
# It assumes your main agent definition and the `create_agent` function
# are in 'adk_gsheet_agent/agent.py'.
AGENT_ENTRYPOINT = "adk_gsheet_agent.agent:create_agent"

def create() -> None:
    """Creates a new deployment for the adk_gsheet_agent."""
    print(f"Attempting to deploy agent '{FLAGS.agent_name}'...")

    # Wrap the agent's builder function in AdkApp for deployment.
    app = reasoning_engines.AdkApp(
        agent_builder=AGENT_ENTRYPOINT, # Points to your 'create_agent' function
        enable_tracing=True,
    )

    # Now deploy to Agent Engine.
    remote_app = agent_engines.create(
        agent_engine=app,
        display_name=FLAGS.agent_name.replace('-', ' ').title(), # Generates a user-friendly display name
        resource_id=FLAGS.agent_name, # The unique ID for the deployed agent
        # Define required Python packages for the deployed environment.
        # This list should include all dependencies from your requirements.txt.
        requirements=[
            "google-cloud-aiplatform[adk,agent_engines]", # Essential for ADK agents
            "pyyaml",
            "google-api-python-client",
            "google-auth-oauthlib",
            "google-cloud-secret-manager",
            # Add any other specific packages your GSheet agent needs here
            # e.g., "pandas", "openpyxl" if you're processing data locally before API calls.
        ],
        # Include your agent's source directory. This bundles your 'adk_gsheet_agent'
        # directory (containing agent.py, config.yaml, etc.) with the deployment.
        extra_packages=[AGENT_SOURCE_DIR],
    )
    print(f"Created remote app: {remote_app.resource_name}")
    print(f"Agent '{FLAGS.agent_name}' deployed successfully!")


def delete(resource_id: str) -> None:
    """Deletes an existing deployment."""
    remote_app = agent_engines.get(resource_id)
    remote_app.delete(force=True)
    print(f"Deleted remote app: {resource_id}")


def list_deployments() -> None:
    """Lists all deployments."""
    deployments = agent_engines.list()
    if not deployments:
        print("No deployments found.")
        return
    print("Deployments:")
    for deployment in deployments:
        print(f"- {deployment.resource_name}")


def create_session(resource_id: str, user_id: str) -> None:
    """Creates a new session for the specified user."""
    remote_app = agent_engines.get(resource_id)
    remote_session = remote_app.create_session(user_id=user_id)
    print("Created session:")
    print(f"  Session ID: {remote_session['id']}")
    print(f"  User ID: {remote_session['user_id']}")
    print(f"  App name: {remote_session['app_name']}")
    print(f"  Last update time: {remote_session['last_update_time']}")
    print("\nUse this session ID with --session_id when sending messages.")


def list_sessions(resource_id: str, user_id: str) -> None:
    """Lists all sessions for the specified user."""
    remote_app = agent_engines.get(resource_id)
    sessions = remote_app.list_sessions(user_id=user_id)
    print(f"Sessions for user '{user_id}':")
    for session in sessions:
        print(f"- Session ID: {session['id']}")


def get_session(resource_id: str, user_id: str, session_id: str) -> None:
    """Gets a specific session."""
    remote_app = agent_engines.get(resource_id)
    session = remote_app.get_session(user_id=user_id, session_id=session_id)
    print("Session details:")
    print(f"  ID: {session['id']}")
    print(f"  User ID: {session['user_id']}")
    print(f"  App name: {session['app_name']}")
    print(f"  Last update time: {session['last_update_time']}")


def send_message(resource_id: str, user_id: str, session_id: str, message: str) -> None:
    """Sends a message to the deployed agent."""
    remote_app = agent_engines.get(resource_id)

    print(f"Sending message to session {session_id} for agent {resource_id}:")
    print(f"Message: {message}")
    print("\nResponse:")
    for event in remote_app.stream_query(
        user_id=user_id,
        session_id=session_id,
        message=message,
    ):
        print(event)


def main(argv=None):
    """Main function that can be called directly or through app.run()."""
    # Parse flags first
    if argv is None:
        argv = flags.FLAGS(sys.argv)
    else:
        argv = flags.FLAGS(argv)

    load_dotenv() # Loads environment variables from a .env file if present

    # Get project, location, and bucket from flags or environment variables
    project_id = (
        FLAGS.project_id if FLAGS.project_id else os.getenv("GOOGLE_PROJECT_ID")
    )
    location = FLAGS.location if FLAGS.location else os.getenv("GOOGLE_CLOUD_LOCATION")
    bucket = FLAGS.bucket if FLAGS.bucket else os.getenv("GOOGLE_CLOUD_STAGING_BUCKET")
    user_id = FLAGS.user_id
    resource_id = FLAGS.agent_name # Use the 'agent_name' flag for the resource_id

    # Validate essential parameters
    if not project_id:
        print("Missing required argument: --project_id or GOOGLE_CLOUD_PROJECT env var.")
        return
    elif not location:
        print("Missing required argument: --location or GOOGLE_CLOUD_LOCATION env var.")
        return
    elif not bucket:
        print("Missing required argument: --bucket or GOOGLE_CLOUD_STAGING_BUCKET env var.")
        return

    # Initialize Vertex AI SDK
    vertexai.init(
        project=project_id,
        location=location,
        staging_bucket=bucket,
    )

    # Execute the chosen action based on the command-line flags
    if FLAGS.create:
        create()
    elif FLAGS.delete:
        delete(resource_id)
    elif FLAGS.list:
        list_deployments()
    elif FLAGS.create_session:
        create_session(resource_id, user_id)
    elif FLAGS.list_sessions:
        list_sessions(resource_id, user_id)
    elif FLAGS.get_session:
        if not FLAGS.session_id:
            print("session_id is required for get_session")
            return
        get_session(resource_id, user_id, FLAGS.session_id)
    elif FLAGS.send:
        if not FLAGS.session_id:
            print("session_id is required for send")
            return
        send_message(resource_id, user_id, FLAGS.session_id, FLAGS.message)
    else:
        print(
            "Please specify one of: --create, --delete, --list, --create_session, --list_sessions, --get_session, or --send"
        )
        print("\nFor deployment operations, specify --project_id, --location, --bucket.")
        print("For session operations, you will also need --agent_name.")


if __name__ == "__main__":
    app.run(main)