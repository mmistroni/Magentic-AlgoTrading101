from pydantic import BaseModel, Field
from typing import List, Dict, Union, Any
class RouteRecommendation(BaseModel):
    summary: str
    cost: float
    duration: int
    is_delayed: bool

class BestRoutesResponse(BaseModel):
    routes: list[RouteRecommendation]
    whatsapp_message: str