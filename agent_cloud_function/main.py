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

    try:
        response = secret_client.access_secret_version(name=ADK_AGENT_URL_SECRET_NAME)
        adk_agent_endpoint = response.payload.data.decode("UTF-8")
    except Exception as e:
        logging.info(f'Failed toa ccess secret:{str(e)}')
        adk_agent_endpoint = str(e)

    if request_json and 'name' in request_json:
        name = request_json['name']
    elif request_args and 'name' in request_args:
        name = request_args['name']
    else:
        name = 'World'
    return f'Hello {name}! Nice to see you. you should have accessed {adk_agent_endpoint} '