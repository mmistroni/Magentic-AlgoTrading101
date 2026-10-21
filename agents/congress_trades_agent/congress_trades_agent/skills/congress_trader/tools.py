from .scripts.fundamentals import fetch_fmp_fundamentals
import json
from datetime import datetime
from typing import Optional, List, Dict, Any
from .scripts.sql_executor import (
    execute_store_decision,
    execute_fetch_decisions
)
from ...schemas import (
    FundamentalEvaluation
    
)

def get_fundamentals(ticker: str) -> FundamentalEvaluation:
    """Fetches key valuation metrics, balance sheet ratios, and fundamental health scores 
    for a given ticker using the underlying FMP script logic.
    """
    result = fetch_fmp_fundamentals(ticker)
    return FundamentalEvaluation(**result)

def store_trade_decision(
    ticker: str,
    action: str,
    conviction_score: float,
    valuation_verdict: str,
    pe_ratio: float,
    notes: str
) -> str:
    """Store a formal trade decision and its structural snapshot into BigQuery episodic memory.
    
    Args:
        ticker: Stock symbol (e.g., 'NVDA', 'MSFT').
        action: Proposed trade action ('BUY', 'SELL', 'HOLD').
        conviction_score: Agent confidence score between 0.0 and 100.0.
        valuation_verdict: Fundamental valuation verdict (e.g., 'UNDERVALUED', 'OVERVALUED').
        pe_ratio: Price-to-earnings ratio at the time of decision.
        notes: Qualitative reasoning or congressional context behind the decision.
    """
    decision_id = f"dec-{ticker.upper()}-{int(datetime.utcnow().timestamp())}"
    decision_timestamp = datetime.utcnow().isoformat() + "Z"
    
    # Build the structured snapshot payload
    snapshot_data = {
        "ticker": ticker.upper(),
        "action": action.upper(),
        "conviction_score": conviction_score,
        "fundamentals": {
            "valuation_verdict": valuation_verdict.upper(),
            "pe_ratio": pe_ratio
        },
        "reasoning_notes": notes
    }
    
    try:
        execute_store_decision(
            decision_id=decision_id,
            ticker=ticker,
            decision_timestamp=decision_timestamp,
            action=action.upper(),
            conviction_score=conviction_score,
            decision_snapshot_json=json.dumps(snapshot_data)
        )
        return f"Successfully stored decision {decision_id} for {ticker.upper()}."
    except Exception as e:
        return f"Error storing decision to BigQuery: {str(e)}"


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
                "decision_snapshot": row.decision_snapshot
            })
        return episodes
    except Exception as e:
        return [{"error": f"Failed to fetch historical episodes: {str(e)}"}]