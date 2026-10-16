from enum import Enum
from typing import List, Dict, Any, Optional, Literal

from pydantic import BaseModel, Field

# ==========================================
# 1. PIPELINE STATE MODELS
# ==========================================

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
    gov_contracts_spend_usd: Optional[float] = 0.0
    gov_contracts_signal: Optional[str] = "Neutral"  # e.g., "High Acceleration", "Moderate", "None"
    gov_contracts_details: Optional[Dict[str, Any]] = None

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


# ==========================================
# 2. CONGRESS RESEARCHER MODELS
# ==========================================

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

class ContractSignalItem(BaseModel):
    action_date: str = Field(description="Date contract award was issued (YYYY-MM-DD)")
    recipient_name: str = Field(description="Name of recipient company")
    ticker: str = Field(description="Stock ticker symbol")
    amount: float = Field(default=0.0, description="Dollar amount of the contract award")
    agency: str = Field(description="Awarding government agency (e.g., NASA, DoD, DHS)")
    description: Optional[str] = Field(default="No contract description provided.", description="Award details")
    formatted_amount: Optional[str] = Field(default=None, description="Human readable amount (e.g. $75M)")

class ContractSignalsResponse(BaseModel):
    ticker: str
    analysis_date: str
    total_contract_spend_usd: float = 0.0
    signals: List[ContractSignalItem] = Field(default_factory=list)
    count: int = 0
    error: Optional[str] = None

class PoliticalContextPayload(BaseModel):
    analysis_date: str = Field(description="ISO date string (YYYY-MM-DD)")
    primary_tickers: List[str] = Field(
        description="Unique list of candidate tickers identified from congress and contract signals"
    )
    congress_signals: List[CongressSignalItem] = Field(
        default_factory=list,
        description="Aggregated congressional buying/selling activity per ticker"
    )
    contract_signals: List[ContractSignalItem] = Field(
        default_factory=list,
        description="Government contract awards fetched for candidate tickers"
    )
    asymmetric_flags: List[str] = Field(
        default_factory=list,
        description="Key anomalies or observations (e.g. 'Strong buying ahead of DoD contract award')"
    )


# ==========================================
# 3. INSIDER ANALYST MODELS
# ==========================================

class Form4SignalItem(BaseModel):
    ticker: str
    issuer: Optional[str] = None
    net_buy_value: float = 0.0
    unique_buyers: int = 0
    is_c_suite_buy: bool = False
    is_cluster_buy: bool = False
    buy_count: int = 0
    sell_count: int = 0
    insider_activity_score: float = 0.0

class Form4SignalsResponse(BaseModel):
    analysis_date: str
    count: int = 0
    signals: List[Form4SignalItem] = Field(default_factory=list)
    error: Optional[str] = None

class LobbyingSignalItem(BaseModel):
    ticker: str
    client_name: Optional[str] = None
    key_issues: Optional[str] = None
    current_spend: float = 0.0
    prior_spend: float = 0.0
    spend_growth_pct: float = 0.0

class LobbyingSignalsResponse(BaseModel):
    analysis_date: str
    count: int = 0
    signals: List[LobbyingSignalItem] = Field(default_factory=list)
    error: Optional[str] = None

class InsiderContextPayload(BaseModel):
    analysis_date: str = Field(description="ISO date string (YYYY-MM-DD)")
    primary_tickers: List[str] = Field(
        description="Unique list of candidate tickers identified from congress and insider/lobbying signals"
    )
    form4_signals: List[Form4SignalItem] = Field(
        default_factory=list,
        description="Aggregated Form 4 filing activity per ticker"
    )
    lobbying_signals: List[LobbyingSignalItem] = Field(
        default_factory=list,
        description="Corporate lobbying expenditures and quarter-over-quarter growth per ticker"
    )
    asymmetric_flags: List[str] = Field(
        default_factory=list,
        description="Key anomalies or observations (e.g. 'Strong executive buying paired with accelerating lobbying spend')"
    )


# ==========================================
# CONGRESS TRADES AGENT MODELS
# ==========================================
class ValuationVerdict(str, Enum):
    UNDERVALUED = "UNDERVALUED"
    FAIRLY_VALUED = "FAIRLY_VALUED"
    OVERVALUED = "OVERVALUED"
    NEUTRAL = "NEUTRAL"

class TradeAction(str, Enum):
    STRONG_BUY = "STRONG_BUY"
    BUY = "BUY"
    HOLD = "HOLD"
    SELL = "SELL"
    STRONG_SELL = "STRONG_SELL"

class FundamentalEvaluation(BaseModel):
    ticker: str  # <--- Add this field here
    pe_ratio: Optional[float] = None
    forward_pe: Optional[float] = None
    debt_to_equity: Optional[float] = None
    free_cash_flow_yield: Optional[float] = None
    return_on_equity: Optional[float] = None
    valuation_verdict: ValuationVerdict = ValuationVerdict.NEUTRAL  # <--- Using Enum here
    fundamental_health_score: float = Field(..., ge=0.0, le=100.0)


class DecisionRationaleBreakdown(BaseModel):
    political_alignment_weight: str  # e.g., "High bipartisan buying intensity"
    insider_confluence_weight: str   # e.g., "Confirmed C-suite cluster purchases"
    fundamental_safety_check: str    # e.g., "P/E ratio at 22.4 supports growth valuation"
    risk_factors: List[str]          # e.g., ["Elevated debt-to-equity ratio", "Regulatory scrutiny"]
    final_synthesis_summary: str     # Detailed prose explaining the 'Why' behind the trade

class TradeSignalSummary(BaseModel):
    ticker: str
    congressional_net_buys: int = 0
    congressional_conviction_score: float = 0.0
    insider_net_buy_value: float = 0.0
    insider_cluster_buy: bool = False
    lobbying_spend: float = 0.0
    contract_value: float = 0.0
    
    # Add normalized 0-100 sub-scores for clean weighting math
    congressional_sub_score: float = 0.0
    insider_sub_score: float = 0.0
    contract_sub_score: float = 0.0
    lobbying_sub_score: float = 0.0

class TickerDecisionRecord(BaseModel):
    decision_id: str
    ticker: str
    decision_timestamp: str
    action: TradeAction  #  # STRONG_BUY, BUY, HOLD, SELL, STRONG_SELL
    conviction_score: float = Field(..., ge=0.0, le=100.0) # Acts as your confluence score
    
    # Capture the weights used for this specific run (Time Zero defaults or historical adjustments)
    weights_applied: Dict[str, float] = Field(
        default={
            "fundamental_health_score": 0.35,
            "insider_sub_score": 0.30,
            "contract_sub_score": 0.15,
            "congressional_sub_score": 0.10,
            "lobbying_sub_score": 0.10,
        }
    )
    
    signals_aggregated: TradeSignalSummary
    fundamentals: FundamentalEvaluation
    rationale: DecisionRationaleBreakdown
    
    # For tracking future performance when evaluating history
    subsequent_performance: Optional[float] = None

class CongressTraderPayload(BaseModel):
    primary_tickers: List[str] = []
    decisions: List[TickerDecisionRecord] = []
    portfolio_macro_stance: str = "RISK_ON"





# ==========================================
# 4. SHARED MARKET MODELS
# ==========================================

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