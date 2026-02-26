from datetime import datetime
import os
# Initialize the synchronous client
from pydantic_tfl_api import JourneyClient
from .models import RouteRecommendation
from typing import List
from datetime import datetime, timedelta
from pydantic_tfl_api.core import ApiError
import zoneinfo
import logging

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
    # In your tools.py
    from_st = "Fairlop Underground Station"
    to_st = "Bromley South Rail Station"
    
    response = client.JourneyResultsByPathFromPathToQueryViaQueryNationalSearchQueryDateQu(
        from_field=from_st,
        to=to_st,         # Bromley South ICS
        date="20260227",
        time="0545",
        nationalSearch=True,      # MANDATORY for Bromley South
        mode="tube,national-rail,overground,elizabeth-line",
        useMultiModalCall=True,
        cyclePreference="None",   # <--- Add this
        bikeProficiency="Easy",
    )

    if isinstance(response, ApiError):
        # This will tell you EXACTLY what is wrong (e.g., "invalid date", "unauthorized")
        print(f"DEBUG: TfL Error {response.http_status_code} -> {response.message}")
        return []

    raw_journeys = response.content.journeys
    print(f'--- Raw journey is:\n{raw_journeys}')
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
    # 1. Join all leg summaries so you know where it's going
    full_route = " -> ".join([leg.instruction.summary for leg in tfl_journey.legs])
    
    # 2. Extract total duration (ensure it's the JOURNEY duration, not leg)
    total_duration = getattr(tfl_journey, 'duration', 0)
    
    # 3. Fare logic (using your confirmed totalCost)
    fare_val = 0.0
    if hasattr(tfl_journey, 'fare') and tfl_journey.fare:
        fare_val = float(getattr(tfl_journey.fare, 'totalCost', 0)) / 100

    return RouteRecommendation(
        summary=full_route,
        cost=fare_val,
        duration=total_duration,
        is_delayed=any(getattr(leg, 'disruptions', []) for leg in tfl_journey.legs)
    )