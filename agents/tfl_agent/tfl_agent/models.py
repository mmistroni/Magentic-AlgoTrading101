from pydantic import BaseModel, Field, ConfigDict
from typing import List, Optional

# --- 1. The Internal Model (What the Tool returns) ---
class SimplifiedJourney(BaseModel):
    duration: int = Field(description="Total travel time in minutes")
    startDateTime: str = Field(description="ISO timestamp for journey start")
    arrivalDateTime: str = Field(description="ISO timestamp for journey end")
    legs_summary: str = Field(
        description="A string of lines used, e.g., 'Central -> Elizabeth -> Southeastern'"
    )
    total_fare: Optional[float] = Field(None, description="The cost in GBP")
    is_disrupted: bool = Field(False, description="TRUE if there is an active delay or closure")
    disruption_messages: List[str] = Field(default_factory=list, description="Specific details of the delay")

# --- 2. The Agent Output Models (What the Agent sends back to you) ---
class RouteRecommendation(BaseModel):
    summary: str = Field(description="The 'legs_summary' from the tool")
    cost: float = Field(description="The 'total_fare' in GBP")
    duration: int = Field(description="Total travel time in minutes")
    is_delayed: bool = Field(description="Must match the 'is_disrupted' status from the tool")
    times: str = Field(description="Formatted string: 'Departs 05:45, Arrives 06:30'")
    reason: str = Field(description="Briefly explain the rank and mention disruptions if any")

class BestRoutesResponse(BaseModel):
    routes: List[RouteRecommendation]
    whatsapp_summary: str = Field(description="A single-sentence summary for a WhatsApp notification")

# --- 3. The API Parsing Models (Used inside the tool logic) ---
class Leg(BaseModel):
    model_config = ConfigDict(extra="ignore")
    duration: int
    instruction: dict 
    # Use aliases if the TfL JSON uses camelCase
    departureTime: str 
    arrivalTime: str