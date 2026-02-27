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
    """A cleaned-up journey route for the agent to analyze."""
    model_config = ConfigDict(extra="ignore")
    
    duration: int = Field(description="Total travel time in minutes")
    start_time: str = Field(alias="startDateTime", description="ISO timestamp of departure")
    arrival_time: str = Field(alias="arrivalDateTime", description="ISO timestamp of arrival")
    legs_summary: List[str] = Field(default=[], description="List of transit lines used (e.g., ['Central Line', 'Thameslink'])")

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