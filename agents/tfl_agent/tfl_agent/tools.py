from pydantic_tfl_api import JourneyClient
from datetime import datetime
import os
# Initialize the synchronous client

from pydantic_tfl_api import JourneyClient

from pydantic_tfl_api import JourneyClient

def get_agent_data(from_stn="940GZZLUFLP", to_stn="940GZZBRMSR"):
    client = JourneyClient(api_token=os.environ['TFL_API_KEY'])
    
    # We use the giant method name you found
    # But we only pass the arguments we actually need!
    response = client.JourneyResultsByPathFromPathToQueryViaQueryNationalSearchQueryDateQu(
        from_field="1000079", 
        to="1000033",
        date="20260218",
        time="0545",
        includeAlternativeRoutes=True
    )
    
    # Access the list of journeys through the .root attribute
    return response.content.journeys