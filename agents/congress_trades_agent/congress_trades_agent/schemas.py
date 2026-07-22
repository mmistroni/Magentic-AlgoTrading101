# state_schema.py
from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from typing import Literal

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

# congress_trades_agent/schemas.py
class LobbyingSignalResponse(BaseModel):
    ticker: str
    company_name: Optional[str] = "N/A"
    total_spend_last_12m: float = 0.0
    latest_filing_date: Optional[str] = "N/A"
    number_of_filings: int = 0
    top_lobbied_issues: List[str] = Field(default_factory=list)
    lobbying_status: str = "Active"
    error: Optional[str] = None

# congress_trades_agent/schemas.py
class CongressSignalItem(BaseModel):
    ticker: str
    signal_date: str
    purchase_count: int = 0
    sale_count: int = 0
    net_buy_activity: int = 0
    buying_days_count: int = 0
    last_trade_date: str
    market_uptrend: bool = True

class CongressSignalsResponse(BaseModel):
    analysis_date: str
    signals: List[CongressSignalItem] = Field(default_factory=list)
    count: int = 0
    error: Optional[str] = None

class FundamentalsResponse(BaseModel):
    ticker: str
    sector: Optional[str] = "Unknown"
    industry: Optional[str] = "Unknown"
    market_cap_B: float = 0.0
    beta: float = 1.0
    forward_pe: float = 0.0
    debt_to_equity: Optional[float] = None
    dividend_yield: float = 0.0
    error: Optional[str] = None

class TradeRecommendation(BaseModel):
    ticker: str = Field(description="Stock ticker symbol")
    action: Literal["STRONG BUY", "BUY", "HOLD", "PASS"] = Field(
        description="Recommended action based on macro regime and confluence filters."
    )
    confidence: int = Field(ge=1, le=10, description="Confidence rating from 1 to 10")
    risk_rating: Literal["Low", "Medium", "High"] = Field(description="Risk assessment level")
    reason: str = Field(
        description="Reasoning in format: 'Thesis: [Macro/Lobbying]. Fundamentals: [Cite P/E & Debt]. Verdict: [Buy/Hold/Pass].'"
    )
