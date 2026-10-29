import json
from datetime import datetime
from typing import Optional, List, Dict, Any

from .scripts.fundamentals import fetch_fmp_fundamentals
from .scripts.sql_executor import (
    execute_store_decision,
    execute_fetch_decisions
)
from congress_trades_agent.schemas import (
    TickerDecisionRecord,
    TradeAction,
    ValuationVerdict,
    TradeSignalSummary,
    FundamentalEvaluation,
    DecisionRationaleBreakdown
)


def get_fundamentals(ticker: str) -> FundamentalEvaluation:
    """Fetches key valuation metrics, balance sheet ratios, and fundamental health scores 
    for a given ticker using the underlying FMP script logic.
    """
    result = fetch_fmp_fundamentals(ticker)
    return FundamentalEvaluation(**result)


def store_trade_decision(
    ticker: str,
    action: str,  # e.g., "BUY", "SELL", "HOLD"
    conviction_score: float,  # Confluence score between 0.0 and 100.0``
    pe_ratio: float,
    valuation_verdict: str,
    fundamental_health_score: float,
    congressional_net_buys: int,
    insider_cluster_buy: bool,
    price: float,
    synthesis_summary: str
) -> str:
    """Validates the trade decision via Pydantic (applying default weights), persists the snapshot to BigQuery, 
    and returns a confirmation message to the agent.
    
    Args:
        ticker: Stock ticker symbol (e.g., 'NVDA').
        action: Final trade action decided by agent ('STRONG_BUY', 'BUY', 'HOLD', 'SELL', 'STRONG_SELL').
        conviction_score: Calculated confluence score between 0.0 and 100.0.
        pe_ratio: P/E ratio from fundamental evaluation.
        valuation_verdict: Valuation category ('UNDERVALUED', 'FAIRLY_VALUED', 'OVERVALUED', 'NEUTRAL').
        fundamental_health_score: Score between 0.0 and 100.0.
        congressional_net_buys: Count of net congressional purchases.
        insider_cluster_buy: Boolean flag for insider cluster activity.
        price: Current stock price.
        synthesis_summary: Detailed prose explaining the 'Why' behind the trade.
    """
    decision_id = f"dec-{ticker.upper()}-{int(datetime.utcnow().timestamp())}"
    decision_timestamp = datetime.utcnow().isoformat() + "Z"
    
    # 1. Build nested sub-models from agent conclusions
    fundamentals = FundamentalEvaluation(
        ticker=ticker.upper(),
        pe_ratio=pe_ratio,
        price = price,
        valuation_verdict=ValuationVerdict(valuation_verdict.upper()),
        fundamental_health_score=fundamental_health_score
    )
    
    signals = TradeSignalSummary(
        ticker=ticker.upper(),
        congressional_net_buys=congressional_net_buys,
        insider_cluster_buy=insider_cluster_buy,
        congressional_sub_score=70.0 if congressional_net_buys > 0 else 50.0,
        insider_sub_score=80.0 if insider_cluster_buy else 50.0
    )
    
    rationale = DecisionRationaleBreakdown(
        political_alignment_weight=f"Congressional net buys: {congressional_net_buys}",
        insider_confluence_weight=f"Insider cluster buy status: {insider_cluster_buy}",
        fundamental_safety_check=f"P/E ratio at {pe_ratio} with verdict {valuation_verdict}",
        risk_factors=["Standard market volatility", "Execution risk"],
        final_synthesis_summary=synthesis_summary
    )
    
    # 2. Instantiate TickerDecisionRecord. 
    # This automatically applies your default weights_applied dict:
    # {"fundamental_health_score": 0.35, "insider_sub_score": 0.30, ...}
    decision_record = TickerDecisionRecord(
        decision_id=decision_id,
        ticker=ticker.upper(),
        decision_timestamp=decision_timestamp,
        action=TradeAction(action.upper()),
        conviction_score=conviction_score,
        signals_aggregated=signals,
        fundamentals=fundamentals,
        rationale=rationale
    )
    
    # 3. Serialize the validated model to JSON specifically for BigQuery snapshot storage
    snapshot_json = decision_record.model_dump_json()
    
    # 4. Execute storage via your BigQuery/SQL script
    try:
        execute_store_decision(
            decision_id=decision_id,
            ticker=ticker.upper(),
            decision_timestamp=decision_timestamp,
            action=action.upper(),
            conviction_score=conviction_score,
            entry_price = price,
            decision_snapshot_json=snapshot_json
        )
        return f"Successfully validated and stored decision record {decision_id} for {ticker.upper()}."
    except Exception as e:
        return f"Error storing decision record to BigQuery: {str(e)}"


def fetch_historical_episodes(
    ticker: Optional[str] = None,
    valuation_verdict: Optional[str] = None,
    min_conviction: float = 0.0,
    limit: int = 5
) -> List[Dict[str, Any]]:
    """Retrieve past trade episodes from BigQuery to evaluate previous performance and reasoning.
    
    Args:
        ticker: Optional stock symbol filter.
        valuation_verdict: Optional valuation category filter (e.g., 'UNDERVALUED').
        min_conviction: Minimum conviction score threshold for retrieved episodes.
        limit: Maximum number of historical episodes to return (default 5).
    """
    try:
        row_iterator = execute_fetch_decisions(
            ticker=ticker,
            valuation_verdict=valuation_verdict,
            min_conviction=min_conviction,
            limit=limit
        )
        
        episodes = []
        for row in row_iterator:
            episodes.append({
                "decision_id": row.decision_id,
                "ticker": row.ticker,
                "timestamp": row.decision_timestamp,
                "action": row.action,
                "conviction_score": row.conviction_score,
                "decision_snapshot": row.decision_snapshot_json
            })
        return episodes
    except Exception as e:
        return [{"error": f"Failed to fetch historical episodes: {str(e)}"}]