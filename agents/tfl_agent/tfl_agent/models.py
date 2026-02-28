from pydantic import BaseModel, Field, ConfigDict
from typing import List, Dict, Union, Any
class RouteRecommendation(BaseModel):
    summary: str
    cost: float
    duration: int
    is_delayed: bool

class BestRoutesResponse(BaseModel):
    routes: list[RouteRecommendation]
    whatsapp_message: str

class SimplifiedJourney(BaseModel):
    duration: int = Field(description="Total travel time in minutes")
    startDateTime: str = Field(description="The ISO timestamp for when the journey begins")
    arrivalDateTime: str = Field(description="The ISO timestamp for when the journey ends")
    # Note: Ensure this type matches what your tool actually returns (list or str)
    legs_summary: str = Field(
        description="MANDATORY: A String representing the list of the specific transport lines used (e.g., ['Central Line', 'Elizabeth line'])"
    )



class Leg(BaseModel):
    model_config = ConfigDict(extra="ignore") # Your shield against "Cycleways" errors
    duration: int
    instruction: dict # Keeps the summary but ignores detailed step validation
    departureTime: str = Field(alias="departureTime")
    arrivalTime: str = Field(alias="arrivalTime")

class Journey(BaseModel):
    model_config = ConfigDict(extra="ignore")
    duration: int
    legs: List[Leg]