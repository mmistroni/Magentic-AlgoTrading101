# short_selling_agent/stage_tools.py

import os
import logging
from google.cloud import bigquery

from .tools import (
    get_bq_short_candidates,
    get_fmp_news,
    get_bearish_insider_sales,
)
from .schemas import MarketLoser
from .state import CURRENT_RUN_STATE
from .schemas import Plus500UniverseReport


# -----------------------------------------------------------------------------
def tool_fetch_bq_candidates(
    as_of_date: str | None = None,
    limit: int = 3
) -> str:
    """
    AGENT INSTRUCTIONS:
      • Call this tool (exactly once in Step 1) to load your top market losers.
      • Pass `as_of_date` as "YYYY-MM-DD" to backtest that historic date; omit or
        pass None to use today’s data.
      • `limit` controls how many tickers to fetch.
      • This appends MarketLoser models into CURRENT_RUN_STATE.dossier.market_losers.
      • Returns the string: "Tickers loaded: TICKER1, TICKER2, …"

    Example:
      tool_fetch_bq_candidates(as_of_date="2023-06-01", limit=5)
    """
    # Delegate to the low-level tool
    rows = get_bq_short_candidates(limit=limit, as_of_date=as_of_date)

    tickers = []
    for r in rows:
        # r is a dict with keys: ticker, price, change_pct, ...
        CURRENT_RUN_STATE.dossier.market_losers.append(
            MarketLoser(
                ticker=r["ticker"],
                price=r["price"],
                change_pct=r["change_pct"]
            )
        )
        tickers.append(r["ticker"])

    return f"Tickers loaded: {', '.join(tickers)}"


# -----------------------------------------------------------------------------
def tool_stage_news(
    ticker: str,
    as_of_date: str | None = None
) -> str:
    """
    AGENT INSTRUCTIONS:
      • Call this tool once per ticker in Step 2 to fetch news.
      • Pass the same `as_of_date` you used in tool_fetch_bq_candidates.
      • Appends a StockNewsReport to CURRENT_RUN_STATE.dossier.news_reports.
      • Returns the string: "Success: News for {ticker} saved to state."

    Example:
      tool_stage_news("AAPL", as_of_date="2023-06-01")
    """
    report = get_fmp_news(ticker, as_of_date=as_of_date)
    CURRENT_RUN_STATE.dossier.news_reports.append(report)
    return f"Success: News for {ticker} saved to state."


# -----------------------------------------------------------------------------
def tool_stage_insiders(
    ticker: str,
    as_of_date: str | None = None
) -> str:
    """
    AGENT INSTRUCTIONS:
      • Call this tool once per ticker in Step 3 to fetch insider sales.
      • Pass the same `as_of_date` you used in tool_fetch_bq_candidates.
      • Appends an InsiderTradingReport to
        CURRENT_RUN_STATE.dossier.insider_reports.
      • Returns the string: "Success: Insiders for {ticker} saved to state."

    Example:
      tool_stage_insiders("AAPL", as_of_date="2023-06-01")
    """
    report = get_bearish_insider_sales(ticker, as_of_date=as_of_date)
    CURRENT_RUN_STATE.dossier.insider_reports.append(report)
    return f"Success: Insiders for {ticker} saved to state."


# -----------------------------------------------------------------------------
def tool_read_full_dossier() -> str:
    """
    AGENT INSTRUCTIONS:
      • Call this tool once, in Step 4, after all market_losers, news_reports,
        and insider_reports have been staged.
      • Returns a JSON string of the full PipelineDossier.

    Example:
      tool_read_full_dossier()
    """
    return CURRENT_RUN_STATE.dossier.model_dump_json(indent=2)


# -----------------------------------------------------------------------------
def get_plus500_universe(
    as_of_date: str | None = None
) -> Plus500UniverseReport:
    """
    Fetches the complete universe of tradable stocks from the Plus500 table,
    either live or as of a historic date.

    AGENT INSTRUCTIONS:
      • Pass `as_of_date` to filter your historical-plus500 table on that date.
      • If omitted, uses the live table (all-time distinct tickers).
      • Returns Plus500UniverseReport(tickers=[...], optional error_message).

    Historical table schema assumed:
      your_project.historical_plus500(
        ticker STRING,
        date DATE
      )

    Example:
      get_plus500_universe(as_of_date="2023-06-01")
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "datascience-projects")

    if as_of_date:
        table = f"`{project_id}.historical_plus500`"
        sql = f"""
          SELECT DISTINCT ticker
          FROM {table}
          WHERE date = @dt
            AND ticker IS NOT NULL
        """
        params = [
            bigquery.ScalarQueryParameter("dt", "DATE", as_of_date)
        ]
    else:
        table = f"`{project_id}.gcp_shareloader.plus500`"
        sql = f"""
          SELECT DISTINCT ticker
          FROM {table}
          WHERE ticker IS NOT NULL
        """
        params = []

    try:
        client = bigquery.Client(project=project_id)
        job = client.query(
            sql,
            job_config=bigquery.QueryJobConfig(query_parameters=params)
        )
        rows = job.result()
        tickers = [row.ticker.strip().upper() for row in rows if row.ticker]
        logging.info(f"Loaded {len(tickers)} Plus500 tickers as_of={as_of_date or 'LIVE'}.")
        return Plus500UniverseReport(tickers=tickers)
    except Exception as e:
        logging.error(f"Failed to fetch Plus500 universe: {e}")
        return Plus500UniverseReport(tickers=[], error_message=str(e))