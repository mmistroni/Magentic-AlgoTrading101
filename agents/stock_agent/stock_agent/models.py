from pydantic import BaseModel, Field, field_validator, model_validator
from typing import List, Optional, Literal

class TechnicalSchema(BaseModel):
    indicators: List[str] = Field(
        description="List of technical indicators like RSI, ADX, SMA.",
        default_factory=list
    )
    volume_metrics: List[str] = Field(
        description="Fields related to volume like OBV or CMF.",
        default_factory=list
    )
    metadata: List[str] = Field(
        description="Core fields like ticker, exchange, or timestamps.",
        default_factory=list
    )

    beta: Optional[float] = Field(
        default=None,
        description="Market sensitivity measure (beta) relative to benchmark (e.g., S&P 500).",
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
    
    @model_validator(mode='before')
    @classmethod
    def debug_input_data(cls, data):
        print(f"DEBUG: ======Pydantic receiving data: {data}")
        return data
    
    @model_validator(mode='after')
    def check_for_empty_discovery(self):
        if not self.indicators and not self.metadata:
            raise ValueError("The Agent failed to map any columns from the discovery tool.")
        return self


class TrendSignal(BaseModel):
    ticker: str
    signal: Literal["BUY", "SELL", "HOLD"]
    confidence_score: float = Field(ge=0, le=1)
    technical_indicators: List[str] = Field(description="List of indicators used (e.g., RSI, MACD)")
    fundamental_metrics: List[str] = Field(description="List of metrics used (e.g., P/E ratio, Revenue Growth)")
    reasoning: str


# ==========================================
# NEW: Batch Container Model for Multi-Ticker Runs
# ==========================================
class BatchMarketReport(BaseModel):
    signals: List[TrendSignal] = Field(
        description="List of individual stock trend signals evaluated during the pipeline run.",
        default_factory=list
    )