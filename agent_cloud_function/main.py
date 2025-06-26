import logging
from google.cloud import secretmanager

ADK_AGENT_URL_SECRET_NAME = "projects/682143946483/secrets/ADK-AGENT-URL"

# Initialize Secret Manager client outside the function to reuse it
# This avoids re-initializing the client for every function invocation
secret_client = secretmanager.SecretManagerServiceClient()

def execute_call(request): 
    """Responds to any HTTP request.
    Args:
        request (flask.Request): The request object.
    Returns:
        The response text, or any set of values that can be turned into a
        Response object using `make_response`.
    """
    request_json = request.get_json(silent=True)
    request_args = request.args
    logging.info('Attempting to access agent url')

    project_number = "682143946483" # Replace with your actual project number if different
    secret_id = "ADK-AGENT-URL" # Replace with your actual secret name

    # Construct the full resource name including the version
    # Using 'latest' is generally recommended for production
    ADK_AGENT_URL_SECRET_NAME = f"projects/{project_number}/secrets/{secret_id}/versions/latest"

    # --- Your original try-except block ---
    try:
        response = secret_client.access_secret_version(name=ADK_AGENT_URL_SECRET_NAME)
        adk_agent_endpoint = response.payload.data.decode("UTF-8")
        logging.info(f'Successfully accessed secret: {secret_id}')
    except Exception as e:
        logging.error(f'Failed to access secret {secret_id}: {str(e)}') # Use error level for failures
        adk_agent_endpoint = "ERROR: Failed to retrieve secret" # Assign a default or handle appropriately
        # Optionally re-raise if this is a critical error for the function
        # raise e

    if request_json and 'name' in request_json:
        name = request_json['name']
    elif request_args and 'name' in request_args:
        name = request_args['name']
    else:
        name = 'World'
    return f'Hello {name}! Nice to see you. you should have accessed {adk_agent_endpoint} '