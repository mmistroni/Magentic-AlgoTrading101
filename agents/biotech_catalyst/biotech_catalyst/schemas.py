# schemas/dossier.py — or wherever you keep models

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ------------------------------
# 1. INPUT DATA MODELS (Keep existing ones)
# ------------------------------
class MarketLoser(BaseModel):
    ticker: str = Field(description="Stock ticker symbol")
    price: float = Field(description="Current price")
    change_pct: float = Field(description="Percentage drop today")

# -----------------------------
# 1. MODELS FOR BQ LOSERS
# -----------------------------
class MarketLoser(BaseModel):
    """Represents a significant market loser."""
    ticker: str = Field(description="Stock ticker symbol")
    price: float = Field(description="Current price")
    change_pct: float = Field(description="Percentage drop today")

class BiggestLosersReport(BaseModel):
    """Report model for the list of biggest market losers from BQ."""
    losers: List[MarketLoser] = Field(description="List of biggest market losers today.")
    error_message: Optional[str] = Field(default=None, description="Error message if fetch failed.")


class NewsArticle(BaseModel):
    date: str = Field(description="Publication date")
    title: str = Field(description="Headline")
    content: str = Field(default="", description="Snippet or body")

class Plus500UniverseReport(BaseModel):
    tickers: List[str] = Field(description="List of tradable ticker symbols on Plus500")
    error_message: Optional[str] = Field(default=None)

class StockNewsReport(BaseModel):
    ticker: str
    articles: List[NewsArticle]
    error_message: Optional[str] = None

class InsiderTrade(BaseModel):
    date: str
    name: str
    title: str
    value_sold: float

class InsiderTradingReport(BaseModel):
    ticker: str
    total_dollars_dumped: float
    significant_sales: List[InsiderTrade]
    error_message: Optional[str] = None


# ------------------------------
# 2. QUANT SIGNAL MODEL (NEW)
# ------------------------------
class QuantitativeSignal(BaseModel):
    """Full technical & fundamental health for a ticker as-of a date."""
    ticker: str

    # Price Structure
    latest_price: Optional[float] = None
    price_below_sma200: Optional[bool] = None
    price_below_sma50: Optional[bool] = None
    sma50_below_sma200: Optional[bool] = None  # Bearish alignment

    # Momentum
    rsi_14: Optional[float] = None
    adx_14: Optional[float] = None  # Trend strength
    choppiness: Optional[float] = None

    # Volume & Short
    volume_ratio_to_avg: Optional[float] = None  # e.g., 1.8x average
    short_interest_pct: Optional[float] = None
    short_squeeze_risk: Optional[bool] = None  # >20% short interest

    # Catalysts
    recent_earnings_miss: Optional[bool] = None
    large_insider_selling: Optional[bool] = None

    # Metadata
    as_of_date: str


# ------------------------------
# 3. AGENT DECISION MODEL
# ------------------------------
from pydantic import BaseModel, Field
from typing import Literal

class QuantDecision(BaseModel):
    ticker: str
    conviction_score: int = Field(ge=0, le=10)  # Gemini-scale: 0–10
    action: Literal["SHORT", "AVOID", "COVER"]
    
    # --- Flattened Audit Fields ---
    overnight_gap_detected: bool = Field(
        False, description="True if the stock gapped down >15% pre-market"
    )
    catalyst_severity: str = Field(
        "None", description="e.g., 'Terminal (Phase 3 Failure)', 'Standard', or 'None'"
    )
    eod_candle_posture: str = Field(
        "Neutral", description="e.g., 'Closed at Lows', 'Recovered', or 'Neutral'"
    )
    # ------------------------------
    
    reasoning: str



# ------------------------------
# 4. UNIFIED PipelineDossier
# ------------------------------
class PipelineDossier(BaseModel):
    """
    The ONE true state object. Evolves through the pipeline.
    """

    # Stage 1: Biggest Movers
    market_losers: List[MarketLoser] = Field(default_factory=list)

    # Stage 2: News Context
    news_reports: List[StockNewsReport] = Field(default_factory=list)

    # Stage 3: Insider Activity
    insider_reports: List[InsiderTradingReport] = Field(default_factory=list)

    # Stage 4: Quantitative Analysis (your new fmp_tools output)
    quant_reports: List[QuantitativeSignal] = Field(default_factory=list)  # ✅ Added

    # Stage 5: Final Agent Decision
    final_decisions: List[QuantDecision] = Field(default_factory=list)  # ✅ Already there

    # Runtime
    as_of_date: Optional[str] = None
    run_id: Optional[str] = None

    # Optional: if you want logging
    metadata: dict = Field(default_factory=dict)


