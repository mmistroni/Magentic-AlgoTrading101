from .scripts.fundamentals import fetch_fmp_fundamentals
from ...schemas import (
    FundamentalEvaluation
    
)


def get_fundamentals(ticker: str) -> FundamentalEvaluation:
    """Fetches key valuation metrics, balance sheet ratios, and fundamental health scores 
    for a given ticker using the underlying FMP script logic.
    """
    result = fetch_fmp_fundamentals(ticker)
    return FundamentalEvaluation(**result)