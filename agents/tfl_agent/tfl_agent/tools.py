from datetime import datetime
import os
# Initialize the synchronous client
from pydantic_tfl_api import JourneyClient
from .models import RouteRecommendation, Leg, Journey, SimplifiedJourney
from typing import List
from datetime import datetime, timedelta
from pydantic_tfl_api.core import ApiError
import zoneinfo
import logging
import httpx

def aaaaaget_tfl_route(travel_date:str, travel_time:str) -> List[RouteRecommendation]:
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

import httpx
from pydantic import BaseModel, ConfigDict, Field
from typing import List, Dict, Any

async def get_tfl_route(travel_date:str, travel_time:str) -> List[SimplifiedJourney]:
    """
    Fetches journeys from TfL.
    Args:
        travel_date: Date in YYYYMMDD format.
        travel_time: Time in HHMM format (24h).
    
    Returns:
        A list of SimplifiedJourney objects containing duration and timing.
        Returns an empty list if a 300 Disambiguation or 404 error occurs.
    """
    from_station: str = "940GZZLUFLP"
    to_station: str = "1007062"
    print(f'------ Fetching route for {travel_date} {travel_time}')
    url = f"https://api.tfl.gov.uk/Journey/JourneyResults/{from_station}/to/{to_station}"
    params = {
        "mode": "tube,national-rail,overground,elizabeth-line",
        "nationalSearch": "true",
        "date": travel_date,
        "time": travel_time,
        "showFares": "true",
        "app_key": f"{os.environ['TFL_API_KEY']}" # Ensure this is in your Codespace env vars
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params)
        
        if response.status_code != 200:
            print(f"==========Failed, status is {response.status_code}=====\n{response.json()}")
            return []

        data = response.json()
        print(f"--- res[ponse from api is:{data}")
        journeys = []
        
        for j in data.get("journeys", []):
            # 1. Extract Line Summary with better logic
            lines = []
            for leg in j.get("legs", []):
                # Try to get the line name (e.g., 'Central'), 
                # fallback to 'Walk' if no routeOptions exist
                route_opts = leg.get("routeOptions", [])
                line_name = route_opts[0].get("name") if route_opts else "Walk"
                lines.append(line_name)
            
            # 2. Format the summary as a string for the Agent
            # This makes it much easier for the LLM to say "Take the Central Line -> Elizabeth Line"
            route_path = " -> ".join(lines)
            
            fare_data = j.get("fare", {})
            total_cost = None
            if fare_data:
                raw_cost = fare_data.get("totalCost")
                if raw_cost is not None:
                    total_cost = raw_cost / 100
            
            journeys.append(SimplifiedJourney(
                duration=j.get("duration"),
                startDateTime=j.get("startDateTime"),
                arrivalDateTime=j.get("arrivalDateTime"),
                legs_summary=route_path,  # Change this to a string in your Pydantic model
                total_fare=total_cost
            ))
            
        return journeys





        return journeys