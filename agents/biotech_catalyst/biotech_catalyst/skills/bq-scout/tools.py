# skills/bq-scout/tools.py (or your appropriate skill directory)

from typing import Optional
from google.adk.tools import FunctionTool, ToolContext

from .scripts.bq_scout_tools import fetch_clinical_signals
from ...schemas import (
    ClinicalSignalResponse, 
    ClinicalSignalItem, 
)


def fetch_clinical_signals_tool(reference_date: str, tool_context: Optional[ToolContext] = None) -> ClinicalSignalResponse:
    """Retrieves terminated or suspended clinical trial signals from BigQuery up to a target reference date.

    Use this tool as the primary entry point to extract negative clinical trial catalysts 
    (e.g., TERMINATED, SUSPENDED, WITHDRAWN) from BigQuery up to the specified `reference_date`. 
    Each returned signal item includes trial metadata, sponsor details, trial title, and failure reasons.

    Args:
        reference_date (str): Cutoff reference timestamp string (e.g., '2025-12-03 23:59:59 UTC').
        tool_context (Optional[ToolContext]): ADK runtime tool context used to update shared pipeline state.

    Returns:
        ClinicalSignalResponse: Pydantic object containing the reference date, total count,
            and a list of ClinicalSignalItem models (or an error message if the query fails).
    """
    try:
        raw_signals = fetch_clinical_signals(reference_date)
        print(f"🔍 Fetched {len(raw_signals)} clinical signal records for {reference_date}")
        
        signal_items = [ClinicalSignalItem(**item) for item in raw_signals]
        response = ClinicalSignalResponse(
            reference_date=reference_date,
            signals=signal_items,
            count=len(signal_items),
        )

        # Mutate shared PipelineState via ADK ToolContext
        if tool_context and signal_items:
            candidates = tool_context.state.get("candidates", [])
            for item in signal_items:
                candidate_dict = {
                    "ticker": item.ticker,
                    "cusip": item.cusip,
                    "sponsor": item.sponsor,
                    "failure_status": item.failure_status,
                    "failure_post_date": item.failure_post_date,
                    "nct_id": item.nct_id,
                    "trial_title": item.trial_title,
                    "failure_reason": item.failure_reason
                }
                # Append or update candidate if not already present
                existing = next((c for c in candidates if c["ticker"] == item.ticker), None)
                if existing:
                    existing.update(candidate_dict)
                else:
                    candidates.append(candidate_dict)
            
            tool_context.state["candidates"] = candidates

        return response

    except Exception as e:
        print(f"❌ Error fetching clinical signals: {e}")
        return ClinicalSignalResponse(
            reference_date=reference_date,
            error=str(e),
        )


# Correctly wrap the wrapper function (not the raw script function)
fetch_clinical_signals_tool = FunctionTool(fetch_clinical_signals_tool)