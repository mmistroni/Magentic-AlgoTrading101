from pydantic import BaseModel, Field
from typing import List, Dict, Union, Any
import random
import time
from datetime import date
from pydantic import BaseModel, Field
from typing import Literal, List

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional

class TechnicalSchema(BaseModel):
    indicators: List[str] = Field(
        description="List of technical indicators like RSI, ADX, SMA."
    )
    volume_metrics: List[str] = Field(
        description="Fields related to volume like OBV or CMF."
    )
    metadata: List[str] = Field(
        description="Core fields like ticker, exchange, or timestamps."
    )
    
    @field_validator('indicators')
    @classmethod
    def check_min_indicators(cls, v):
        if len(v) < 2:
            raise ValueError("Strategic analysis requires at least 2 indicators for confluence.")
        return v

    @field_validator('metadata')
    @classmethod
    def must_have_identity(cls, v):
        if not any(item.lower() in ['ticker', 'symbol'] for item in v):
            raise ValueError("Identity field (ticker/symbol) missing from schema.")
        return v
class TrendSignal(BaseModel):
    ticker: str
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence_score: float = Field(ge=0, le=1)
    technical_indicators: List[str] = Field(description="List of indicators used (e.g., RSI, MACD)")
    fundamental_metrics: List[str] = Field(description="List of metrics used (e.g., P/E ratio, Revenue Growth)")
    reasoning: str