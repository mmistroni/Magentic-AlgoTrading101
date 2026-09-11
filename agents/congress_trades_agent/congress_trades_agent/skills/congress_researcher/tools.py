# skills/CongressResearcher/tools.py

from google.adk.tools import FunctionTool
from .scripts.congress_signals import get_bq_data
from .scripts.gov_contracts import get_bq_signals_data
from ...schemas import (
    CongressSignalsResponse, 
    CongressSignalItem, 
    ContractSignalsResponse, 
    ContractSignalItem
)


def fetch_congress_signals(analysis_date: str) -> CongressSignalsResponse:
    """Retrieves high-conviction stock purchase signals from Congressional trading activity up to a target analysis date.

    Use this tool as the primary entry point to identify stock candidates accumulated by members of 
    Congress. The underlying query filters for positive net buy activity (minimum 2 distinct buying days) 
    over a 90-day lookback window up to `analysis_date`, excluding non-individual stock noise (e.g. ETFs).
    Each returned signal item includes trade metadata, purchase/sale counts, and the SPY 200-day SMA 
    macro market regime status (`market_uptrend`).

    Args:
        analysis_date (str): Cutoff reference date in 'YYYY-MM-DD' format (e.g. '2026-06-30').

    Returns:
        CongressSignalsResponse: Pydantic object containing the analysis date, total count, 
            and a list of CongressSignalItem models (or an error message if the query fails).
    """
    try:
        raw_signals = get_bq_data(analysis_date)
        print(f"🔍 Fetched {len(raw_signals)} high-conviction signals for {analysis_date}")
        
        signal_items = [CongressSignalItem(**item) for item in raw_signals]
        return CongressSignalsResponse(
            analysis_date=analysis_date,
            signals=signal_items,
            count=len(signal_items),
        )
    except Exception as e:
        print(f"❌ Error fetching congress signals: {e}")
        return CongressSignalsResponse(
            analysis_date=analysis_date,
            error=str(e),
        )

def fetch_contract_signals(ticker: str, analysis_date: str) -> ContractSignalsResponse:
    """Retrieves US Government contract award signals from BigQuery for a specific corporate stock ticker 
    up to a target analysis date.

    Use this tool to cross-reference identified stock candidates with federal procurement actions 
    (e.g., NASA, DoD, DHS contract awards) awarded ON OR BEFORE `analysis_date`. This avoids look-ahead 
    bias when correlating Congressional trades with historical government spending.

    Args:
        ticker (str): Target stock ticker symbol (e.g. 'LMT', 'NOC', 'PLTR').
        analysis_date (str): Cutoff reference date in 'YYYY-MM-DD' format (e.g. '2026-06-30').

    Returns:
        ContractSignalsResponse: Pydantic object containing the ticker symbol, total combined contract 
            spend in USD up to analysis_date, signal count, and a list of ContractSignalItem models.
    """
    try:
        raw_signals = get_bq_signals_data(ticker=ticker, analysis_date=analysis_date)
        print(f"🔍 Fetched {len(raw_signals)} contract signals for {ticker} up to {analysis_date}")
        
        signal_items = [ContractSignalItem(**item) for item in raw_signals]
        return ContractSignalsResponse(
            ticker=ticker,
            analysis_date=analysis_date,
            total_contract_spend_usd=sum(item.amount for item in signal_items),
            signals=signal_items,
            count=len(signal_items),
        )
    except Exception as e:
        print(f"❌ Error fetching contract signals: {e}")
        return ContractSignalsResponse(
            ticker=ticker,
            analysis_date=analysis_date,
            error=str(e),
        )

# Wrapped ADK FunctionTool
fetch_congress_signals_tool = FunctionTool(fetch_congress_signals)
fetch_contract_signals_tool = FunctionTool(fetch_contract_signals)