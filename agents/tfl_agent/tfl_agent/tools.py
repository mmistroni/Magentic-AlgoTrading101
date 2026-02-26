from datetime import datetime
import os
# Initialize the synchronous client
from pydantic_tfl_api import JourneyClient
from .models import RouteRecommendation
from typing import List
from datetime import datetime, timedelta
import zoneinfo

def get_tfl_route(travel_date:str, travel_time:str) -> List[RouteRecommendation]:
    """
    Fetches journeys from TfL.
    Args:
        travel_date: Date in YYYYMMDD format.
        travel_time: Time in HHMM format (24h).
    """
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
    raw_journeys = response.content.journeys
    recommendations = [_map_tfl_to_recommendation(j) for j in raw_journeys]
    
    return recommendations
    
from datetime import datetime, timedelta
import zoneinfo

def resolve_date_string(date_input: str) -> dict:
    """
    Resolves relative date terms like 'today' or 'tomorrow' into YYYYMMDD.
    If a specific date is passed (e.g. '2026-03-01'), it formats it correctly.
    """
    london_tz = zoneinfo.ZoneInfo("Europe/London")
    now = datetime.now(london_tz)
    
    clean_input = date_input.lower().strip()
    
    if clean_input == "today":
        target_date = now
    elif clean_input == "tomorrow":
        target_date = now + timedelta(days=1)
    elif clean_input == "yesterday":
        target_date = now - timedelta(days=1)
    else:
        # Fallback: Try to parse a standard date string if the LLM sends one
        try:
            target_date = datetime.strptime(clean_input, "%Y-%m-%d")
        except ValueError:
            return {"error": f"Could not resolve date: {date_input}", "status": "failure"}

    resolved_str = target_date.strftime("%Y%m%d")
    return {
        "resolved_date": resolved_str,
        "human_readable": target_date.strftime("%A, %d %B %Y"),
        "status": "success"
    }

def _map_tfl_to_recommendation(tfl_journey) -> RouteRecommendation:
    # 1. Determine if there are delays
    # We check every 'leg' of the journey for disruption messages
    has_delays = any(getattr(leg, 'disruptions', []) for leg in tfl_journey.legs)
    
    # 2. Extract Fare (TfL sometimes puts this in a list)
    # Default to 0.0 if not found
    fare_val = 0.0
    if hasattr(tfl_journey, 'fare') and tfl_journey.fare:
        fare_val = tfl_journey.fare.total_fare / 100  # Convert pence to GBP

    # 3. Create the simplified model
    return RouteRecommendation(
        summary=f"Journey via {tfl_journey.legs[0].instruction.summary}",
        cost=fare_val,
        duration=tfl_journey.duration,
        is_delayed=has_delays
    )