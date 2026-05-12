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
    as_of_date: str ="",
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

    if not tickers:
        return f"No tickers found for date {as_of_date}."

    return f"Tickers loaded: {', '.join(tickers)}"


# -----------------------------------------------------------------------------
def tool_stage_news(
    ticker: str,
    as_of_date: str = ""
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
    as_of_date: str = ""
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
# tools/stage_tools.py or agent_tools.py
from short_selling_agent.schemas import CURRENT_RUN_STATE

def tool_read_full_dossier() -> str:
    """
    Call this after all staging steps.
    Returns full JSON of the dossier — visible to the next agent.
    """
    return CURRENT_RUN_STATE.dossier.model_dump_json(indent=2)


# -----------------------------------------------------------------------------
def get_plus500_universe(
    as_of_date: str = ""
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
    

# stage_tools.py (add this function)

import os
from typing import Dict, Any
import fmp_tools  # ← Your fmp_tools.py

# short_selling_agent/stage_tools.py

from typing import Any

def tool_stage_quant_data(ticker: str, as_of_date: str) -> None:
    """
    ✅ Fetches quantitative data using fmp_tools
    ✅ Stages it as a Pydantic QuantitativeSignal
    ✅ Appends to PipelineDossier.quant_reports
    ✅ No manual dicts — full schema compliance
    """
    from short_selling_agent.state import CURRENT_RUN_STATE
    from short_selling_agent.schemas import QuantitativeSignal  # Make sure this exists

    try:
        # Use your fmp_tools to fetch full data as of that date
        data = fmp_tools.get_all_data_for_ticker(
            symbol=ticker,
            as_of_date=as_of_date,
            lookback_days=180
        )

        if not data['price']:
            return  # Nothing to stage

        # ------------------------------
        # Extract: Price & Trend
        # ------------------------------
        price = data['price'][-1]['adjClose']
        sma200_val = data['indicators']['sma200'][-1]['value'] if data['indicators']['sma200'] else None
        sma50_val = data['indicators']['sma50'][-1]['value'] if data['indicators']['sma50'] else None
        price_below_sma200 = (price < sma200_val) if (price and sma200_val) else None
        price_below_sma50 = (price < sma50_val) if (price and sma50_val) else None
        sma50_below_sma200 = (sma50_val < sma200_val) if (sma50_val and sma200_val) else None

        # ------------------------------
        # Extract: Momentum
        # ------------------------------
        rsi_val = data['indicators']['rsi'][-1]['value'] if data['indicators']['rsi'] else None
        adx_val = data['indicators']['adx'][-1]['value'] if data['indicators']['adx'] else None

        # ------------------------------
        # Extract: Volume (vs avg)
        # ------------------------------
        volumes = [p['volume'] for p in data['price'][-20:]]
        avg_volume = sum(volumes) / len(volumes) if volumes else None
        current_volume = data['price'][-1]['volume']
        volume_ratio = (current_volume / avg_volume) if avg_volume else None

        # ------------------------------
        # Extract: Short Interest
        # ------------------------------
        short_info = data['fundamentals']['short_interest']
        short_pct = short_info['shortPercent']  # Already a float (e.g., 0.235)
        short_pct_pct = round(short_pct * 100, 1) if short_pct else None
        short_squeeze_risk = short_pct > 0.20 if short_pct else None  # >20%

        # ------------------------------
        # Extract: Catalysts
        # ------------------------------
        earnings_list = data['fundamentals']['recent_earnings']
        recent_earnings_miss = (
            any(e['surprise'] and e['surprise'] < -0.1 for e in earnings_list)
            if earnings_list else None
        )

        insider_selling_events = len([
            t for t in data['fundamentals']['recent_earnings']
            if t.get('transaction_type') == 'SELL' and (t.get('value_sold', 0) > 1e6)
        ])
        large_insider_selling = insider_selling_events >= 2

        # ------------------------------
        # Build QuantitativeSignal (Pydantic model)
        # ------------------------------
        quant_signal = QuantitativeSignal(
            ticker=ticker,

            # Price & Trend
            latest_price=round(float(price), 2) if price else None,
            price_below_sma200=price_below_sma200,
            price_below_sma50=price_below_sma50,
            sma50_below_sma200=sma50_below_sma200,

            # Momentum
            rsi_14=round(rsi_val, 1) if rsi_val else None,
            adx_14=round(adx_val, 1) if adx_val else None,

            # Volume
            volume_ratio_to_avg=round(float(volume_ratio), 2) if volume_ratio else None,

            # Short Interest & Risk
            short_interest_pct=short_pct_pct,
            short_squeeze_risk=short_squeeze_risk,

            # Catalysts
            recent_earnings_miss=recent_earnings_miss,
            large_insider_selling=large_insider_selling,

            # Metadata
            as_of_date=as_of_date
        )

        # ------------------------------
        # Append to Dossier
        # ------------------------------
        CURRENT_RUN_STATE.dossier.quant_reports.append(quant_signal)

        # Optional: log
        # print(f"📊 Staged quant signal for {ticker} | RSI: {rsi_val}, Short: {short_pct_pct}%")

    except Exception as e:
        print(f"❌ Error staging quant data for {ticker}: {str(e)}")
        # Don't crash — continue pipeline