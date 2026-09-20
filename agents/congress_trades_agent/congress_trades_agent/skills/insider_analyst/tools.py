from google.adk.tools import FunctionTool
from typing import Optional

from .scripts.insider_signals import get_form4_data
from .scripts.lobbying_signals import get_lobbying_data
from ...schemas import (
    Form4SignalsResponse,
    Form4SignalItem,
    LobbyingSignalsResponse,
    LobbyingSignalItem,
)


def fetch_form4_signals(analysis_date: str, ticker: Optional[str] = None) -> Form4SignalsResponse:
    """Retrieves discretionary open-market executive stock purchases (Form 4) from BigQuery.

    Executes parameterized SQL against form4_master, filtering out automated 10b5-1 
    transactions to compute net executive buying, cluster buy flags, and C-suite participation.

    Args:
        analysis_date (str): Point-in-time cutoff reference date in 'YYYY-MM-DD' format.
        ticker (str, optional): Target ticker symbol to filter results.

    Returns:
        Form4SignalsResponse: Structured Pydantic response with insider trade metrics.
    """
    try:
        raw_signals = get_form4_data(analysis_date=analysis_date, ticker=ticker)
        print(f"🔍 [fetch_form4_signals] Fetched {len(raw_signals)} Form 4 records for date {analysis_date}")

        signal_items = [Form4SignalItem(**item) for item in raw_signals]
        return Form4SignalsResponse(
            analysis_date=analysis_date,
            signals=signal_items,
            count=len(signal_items),
        )
    except Exception as e:
        print(f"❌ [fetch_form4_signals] Error retrieving Form 4 signals: {e}")
        return Form4SignalsResponse(
            analysis_date=analysis_date,
            error=str(e),
        )


def fetch_lobbying_signals(analysis_date: str, ticker: Optional[str] = None) -> LobbyingSignalsResponse:
    """Retrieves corporate lobbying expenditures and quarterly growth metrics from BigQuery.

    Executes parameterized CTE-based SQL against lobbying_signals, calculating quarter-over-quarter 
    spending deltas and aggregating target legislative issue codes.

    Args:
        analysis_date (str): Point-in-time cutoff reference date in 'YYYY-MM-DD' format.
        ticker (str, optional): Target ticker symbol to filter results.

    Returns:
        LobbyingSignalsResponse: Structured Pydantic response with lobbying spend metrics.
    """
    try:
        raw_signals = get_lobbying_data(analysis_date=analysis_date, ticker=ticker)
        print(f"🔍 [fetch_lobbying_signals] Fetched {len(raw_signals)} lobbying records for date {analysis_date}")

        signal_items = [LobbyingSignalItem(**item) for item in raw_signals]
        return LobbyingSignalsResponse(
            analysis_date=analysis_date,
            signals=signal_items,
            count=len(signal_items),
        )
    except Exception as e:
        print(f"❌ [fetch_lobbying_signals] Error retrieving lobbying signals: {e}")
        return LobbyingSignalsResponse(
            analysis_date=analysis_date,
            error=str(e),
        )


# ADK FunctionTool Wrappers for sub-agent registration
fetch_form4_signals_tool = FunctionTool(fetch_form4_signals)
fetch_lobbying_signals_tool = FunctionTool(fetch_lobbying_signals)