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


# --- TOOL 2: STATION RESOLVER (The Fix) ---
async def get_station_id(name: str) -> str:
    """Matches a name to a Naptan ID to prevent '300 Multiple Choice' errors."""
    url = f"https://api.tfl.gov.uk/StopPoint/Search/{name}"
    async with httpx.AsyncClient() as client:
        try:
            r = await client.get(url, params={"app_key": os.environ.get('TFL_API_KEY')})
            if r.status_code == 200 and r.json().get("matches"):
                # Returns the first specific station ID (e.g., 940GZZLUDHK)
                return r.json()["matches"][0]["id"]
        except Exception as e:
            logger.error(f"Search failed for {name}: {e}")
    return name # Fallback to original name if search fails

async def get_tfl_route(travel_date: str, travel_time: str = "0545") -> List[SimplifiedJourney]:
    """
    Final Fix: Uses ICS Codes and includes all necessary modes for Denmark Hill.
    """
    # ICS Codes are the numeric 'Master IDs' for these stations
    from_id = "1000079"  # Fairlop (ICS Code)
    to_id = "1001083"    # Denmark Hill (ICS Code)
    
    url = f"https://api.tfl.gov.uk/Journey/JourneyResults/{from_id}/to/{to_id}"
    
    params = {
        "date": travel_date,
        "time": travel_time,
        # WE MUST INCLUDE national-rail OR DENMARK HILL WON'T BE 'IDENTIFIED'
        "mode": "tube,overground,national-rail", 
        "app_key": os.environ.get('TFL_API_KEY')
    }

    async with httpx.AsyncClient() as client:
        response = await client.get(url, params=params, timeout=20.0)
        
        # Log for debugging if it fails again
        if response.status_code != 200:
            logger.error(f"TfL Error: {response.status_code}")
            return []

        data = response.json()
        journeys = []
        
        for j in data.get("journeys", []):
            # Extract line names from 'routeOptions'
            lines = []
            for leg in j.get("legs", []):
                name = leg.get("routeOptions", [{}])[0].get("name", "Walk")
                lines.append(name)
            
            disruptions = [d.get("description") for leg in j.get("legs", []) for d in leg.get("disruptions", [])]
            
            #Helper to format "2026-03-20T05:45:00" -> "05:45"
            def format_time(dt_str):
                if not dt_str: return "N/A"
                return datetime.fromisoformat(dt_str).strftime("%H:%M")

            dep_time = format_time(j.get("startDateTime"))
            arr_time = format_time(j.get("arrivalDateTime"))


            # Fare (pence to pounds)
            raw_fare = j.get("fare", {}).get("totalCost")
            total_fare = float(raw_fare) / 100 if raw_fare is not None else None

            journeys.append(SimplifiedJourney(
                duration=j.get("duration"),
                startDateTime=dep_time,
                arrivalDateTime=arr_time,
                legs_summary=" -> ".join(lines),
                total_fare=total_fare,
                is_disrupted=len(disruptions) > 0,
                disruption_messages=list(set(disruptions))
            ))
            
        return journeys

