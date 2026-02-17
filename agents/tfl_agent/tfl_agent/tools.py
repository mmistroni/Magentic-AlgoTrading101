from pydantic_tfl_api import JourneyClient
from datetime import datetime
import os
# Initialize the synchronous client
client = JourneyClient(api_token=os.environ['TFL_API_KEY'])

def get_agent_data():
    # Fetch journey results
    # The library automatically maps the JSON to Pydantic objects
    response = client.get_journey_results(
        from_path="940GZZLUFLP", # Fairlop Naptan
        to_path="940GZZBRMSR",   # Bromley South Naptan
        date="20260218",         # Tomorrow's date
        time="0545",
        include_alternative_routes=True
    )
    
    # Extract the journeys
    all_journeys = response.content.journeys
    
    # Now your Agent can sort these by duration and price!
    return all_journeys