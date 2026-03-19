import os
import httpx
import zoneinfo
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any
from .models import SimplifiedJourney

# Configure logging for better visibility in Cloud Run
logger = logging.getLogger(__name__)

def resolve_date_string(date_input: str) -> dict:
    """
    Resolves relative date terms like 'today' or 'tomorrow' into YYYYMMDD.
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
        try:
            # Handle YYYY-MM-DD input from LLM
            target_date = datetime.strptime(clean_input, "%Y-%m-%d")
        except ValueError:
            return {"error": f"Could not resolve date: {date_input}", "status": "failure"}

    return {
        "resolved_date": target_date.strftime("%Y%m%d"),
        "human_readable": target_date.strftime("%A, %d %B %Y"),
        "status": "success"
    }

async def get_tfl_route(travel_date: str, 
                        travel_time: str = "0545") -> List[SimplifiedJourney]:
    """
    Fetches journeys from TfL with disruption detection and National Rail support.
    """
    url = f"https://api.tfl.gov.uk/Journey/JourneyResults/{from_id}/to/{to_id}"
    
    params = {
        "date": travel_date,
        "time": travel_time,
        "nationalSearch": "true",
        "app_key": os.environ.get('TFL_API_KEY')
    }

    async with httpx.AsyncClient() as client:
        try:
            response = await client.get(url, params=params, timeout=20.0)
            
            if response.status_code == 300:
                data = response.json()
                # Extract the first suggested Naptan IDs from the "choices"
                best_from = data.get("fromStopPointProfiles", [{}])[0].get("naptanId", from_id)
                best_to = data.get("toStopPointProfiles", [{}])[0].get("naptanId", to_id)
                
                print(f"⚠️ 300 Error: Disambiguating to {best_from} -> {best_to}")
                # Recursively call with the "correct" IDs
                return await get_tfl_route(best_from, best_to, travel_date, travel_time)


            if response.status_code != 200:
                print(f"❌ TfL API Failure: {response.status_code}")
                return []

            data = response.json()
            journeys = []
            print(f'Data is:\n{data}')
            for j in data.get("journeys", []):
                # --- 1. Line Summary & Disruption Detection ---
                lines = []
                is_disrupted = False
                disruption_notes = []
                
                for leg in j.get("legs", []):
                    # Get Line Name
                    route_opts = leg.get("routeOptions", [])
                    line_name = route_opts[0].get("name") if route_opts else "Walk"
                    lines.append(line_name)
                    
                    # Extract Disruptions
                    leg_disruptions = leg.get("disruptions", [])
                    if leg_disruptions:
                        is_disrupted = True
                        for d in leg_disruptions:
                            # Use 'description' for the human-readable delay text
                            disruption_notes.append(d.get("description", "Service delay reported"))
                
                # --- 2. Fare Calculation ---
                fare_data = j.get("fare", {})
                total_cost = None
                if fare_data:
                    raw_cost = fare_data.get("totalCost")
                    if raw_cost is not None:
                        total_cost = float(raw_cost) / 100
                
                # --- 3. Build Model ---
                journeys.append(SimplifiedJourney(
                    duration=j.get("duration"),
                    startDateTime=j.get("startDateTime"),
                    arrivalDateTime=j.get("arrivalDateTime"),
                    legs_summary=" -> ".join(lines),
                    total_fare=total_cost,
                    is_disrupted=is_disrupted,
                    disruption_messages=list(set(disruption_notes)) # Unique notes only
                ))
                
            return journeys

        except Exception as e:
            print(f"💥 Error in get_tfl_route: {str(e)}")
            return []