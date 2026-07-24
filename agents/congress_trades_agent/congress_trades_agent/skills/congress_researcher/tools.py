# skills/CongressResearcher/tools.py

from google.adk.tools import FunctionTool
from .scripts.fetch_congress_data import get_bq_data
from ...schemas import CongressSignalsResponse, CongressSignalItem

def fetch_congress_signals(analysis_date: str) -> CongressSignalsResponse:
    """
    Primary Entry Point: Retrieves 'High Conviction' Congress trading signals for a specific date.
    
    Use this tool to obtain initial stock candidates based on insider Congress trading activity.
    It executes a query filtering for positive net buy activity (at least 2 buying days) over 
    a 90-day lookback window to identify coordinated insider buying while filtering out spammed trades.
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

# Wrapped ADK FunctionTool
fetch_congress_signals_tool = FunctionTool(fetch_congress_signals)