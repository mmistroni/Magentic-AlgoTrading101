# skills/InsiderAnalyst/tools.py

from typing import Optional
from google.adk.tools import FunctionTool, ToolContext
from .scripts.form4_signals import get_bq_form4_data
from .scripts.lobbying_signals import get_bq_lobbying_data
from ...schemas import (
    Form4SignalsResponse,
    Form4SignalItem,
    LobbyingSignalsResponse,
    LobbyingSignalItem,
    ConfluenceReport,
)


def fetch_form4_signals(
    ticker: str,
    analysis_date: str,
    tool_context: Optional[ToolContext] = None,
) -> Form4SignalsResponse:
    """Retrieves SEC Form 4 insider trading signals for a specific stock ticker up to analysis_date.

    Args:
        ticker (str): Target stock ticker symbol (e.g., 'JEF', 'AAPL').
        analysis_date (str): Cutoff reference date in 'YYYY-MM-DD' format.
        tool_context (Optional[ToolContext]): ADK runtime tool context used to update shared pipeline state.

    Returns:
        Form4SignalsResponse: Pydantic response containing insider transaction signals.
    """
    try:
        raw_signals = get_bq_form4_data(ticker=ticker, analysis_date=analysis_date)
        print(f"🔍 Fetched {len(raw_signals)} Form 4 signals for {ticker} up to {analysis_date}")

        signal_items = [Form4SignalItem(**item) for item in raw_signals]

        response = Form4SignalsResponse(
            analysis_date=analysis_date,
            signals=signal_items,
            count=len(signal_items),
        )

        # Mutate shared PipelineState via ADK ToolContext
        if tool_context and signal_items:
            # 1. Determine form4_signal classification
            c_suite_buy = any(item.is_c_suite_buy for item in signal_items)
            cluster_buy = any(item.is_cluster_buy for item in signal_items)

            if cluster_buy and c_suite_buy:
                form4_signal = "High Conviction Cluster Buy"
            elif cluster_buy:
                form4_signal = "Cluster Buy"
            elif c_suite_buy:
                form4_signal = "C-Suite Accumulation"
            else:
                form4_signal = "Moderate"

            # 2. Update confluence_reports state
            confluence_reports = tool_context.state.get("confluence_reports", {})
            raw_report = confluence_reports.get(ticker, {})

            # Ensure dictionary or object compatibility
            if isinstance(raw_report, ConfluenceReport):
                report_dict = raw_report.model_dump()
            elif isinstance(raw_report, dict):
                report_dict = raw_report
            else:
                report_dict = {}

            report_dict.update({
                "form4_signal": form4_signal,
                "form4_details": response.model_dump(),
            })

            confluence_reports[ticker] = report_dict
            tool_context.state["confluence_reports"] = confluence_reports

        return response

    except Exception as e:
        print(f"❌ Error fetching Form 4 signals: {e}")
        return Form4SignalsResponse(
            analysis_date=analysis_date,
            error=str(e),
        )


def fetch_lobbying_signals(
    ticker: str,
    analysis_date: str,
    tool_context: Optional[ToolContext] = None,
) -> LobbyingSignalsResponse:
    """Retrieves corporate lobbying expenditures and key issue signals for a ticker up to analysis_date.

    Args:
        ticker (str): Target stock ticker symbol (e.g., 'WYNN', 'LMT').
        analysis_date (str): Cutoff reference date in 'YYYY-MM-DD' format.
        tool_context (Optional[ToolContext]): ADK runtime tool context used to update shared pipeline state.

    Returns:
        LobbyingSignalsResponse: Pydantic response containing corporate lobbying spend signals.
    """
    try:
        raw_signals = get_bq_lobbying_data(ticker=ticker, analysis_date=analysis_date)
        print(f"🔍 Fetched {len(raw_signals)} lobbying signals for {ticker} up to {analysis_date}")

        signal_items = [LobbyingSignalItem(**item) for item in raw_signals]
        total_lobbying_spend = sum(item.current_spend for item in signal_items)

        response = LobbyingSignalsResponse(
            analysis_date=analysis_date,
            signals=signal_items,
            count=len(signal_items),
        )

        # Mutate shared PipelineState via ADK ToolContext
        if tool_context:
            confluence_reports = tool_context.state.get("confluence_reports", {})
            raw_report = confluence_reports.get(ticker, {})

            if isinstance(raw_report, ConfluenceReport):
                report_dict = raw_report.model_dump()
            elif isinstance(raw_report, dict):
                report_dict = raw_report
            else:
                report_dict = {}

            report_dict.update({
                "lobbying_spend_usd": total_lobbying_spend,
                "lobbying_details": response.model_dump(),
            })

            confluence_reports[ticker] = report_dict
            tool_context.state["confluence_reports"] = confluence_reports

        return response

    except Exception as e:
        print(f"❌ Error fetching lobbying signals: {e}")
        return LobbyingSignalsResponse(
            analysis_date=analysis_date,
            error=str(e),
        )


# Wrapped ADK FunctionTools
fetch_form4_signals_tool = FunctionTool(fetch_form4_signals)
fetch_lobbying_signals_tool = FunctionTool(fetch_lobbying_signals)