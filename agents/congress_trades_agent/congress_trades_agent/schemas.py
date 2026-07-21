# state_schema.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field

class CandidateTicker(BaseModel):
    ticker: str
    buying_days_count: int
    net_buy_activity: int
    purchase_count: int
    sale_count: int
    last_trade_date: str

class ConfluenceReport(BaseModel):
    form4_signal: Optional[str] = "Neutral"
    form4_details: Optional[Dict[str, Any]] = None
    lobbying_spend_usd: Optional[float] = 0.0
    lobbying_details: Optional[Dict[str, Any]] = None

class TradeReasoning(BaseModel):
    macro_context: str
    confluence_signals: str
    fundamentals: str
    safety_rails: str
    verdict: str

class FinalDecision(BaseModel):
    ticker: str
    action: str  # "STRONG BUY", "BUY", "HOLD", "PASS"
    confidence: int
    risk_rating: str  # "Low", "Medium", "High"
    reasoning: TradeReasoning

class PipelineState(BaseModel):
    analysis_date: str
    macro_summary: Optional[str] = None
    candidates: List[CandidateTicker] = Field(default_factory=list)
    confluence_reports: Dict[str, ConfluenceReport] = Field(default_factory=dict)
    final_dossier: List[FinalDecision] = Field(default_factory=list)

# tool_schemas.py
from typing import Optional, Dict, Any
from pydantic import BaseModel, Field

class Form4SignalResponse(BaseModel):
    ticker: str
    insider_title: Optional[str] = "Insider"
    transaction_type: Optional[str] = "None"
    shares: Optional[int] = 0
    transaction_date: Optional[str] = "N/A"
    is_officer: bool = False
    is_director: bool = False
    signal_strength: str = "Neutral"
    error: Optional[str] = None


class FundamentalsResponse(BaseModel):
    ticker: str
    market_cap: Optional[float] = None
    forward_pe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    sector: Optional[str] = None
    valid: bool
    error: Optional[str] = None
