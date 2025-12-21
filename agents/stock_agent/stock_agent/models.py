from pydantic import BaseModel, Field
from typing import List, Dict, Union, Any
import random
import time
from datetime import date
from pydantic import BaseModel, Field
from typing import Literal, List

class TrendSignal(BaseModel):
    ticker: str
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence_score: float = Field(ge=0, le=1)
    technical_indicators: List[str] = Field(description="List of indicators used (e.g., RSI, MACD)")
    fundamental_metrics: List[str] = Field(description="List of metrics used (e.g., P/E ratio, Revenue Growth)")
    reasoning: str