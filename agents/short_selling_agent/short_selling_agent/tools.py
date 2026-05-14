# short_selling_agent/tools.py

import os
import logging
import requests
from datetime import datetime, timedelta
from google.cloud import bigquery

from .schemas import (
    BiggestLosersReport,
    MarketLoser,
    StockNewsReport,
    NewsArticle,
    InsiderTradingReport,
    InsiderTrade,
)


# -----------------------------------------------------------------------------
def get_fmp_bigger_losers(
    limit: int = 5,
    as_of_date: str | None = None
) -> BiggestLosersReport:
    """
    Fetch biggest losers either live or for a historical date.

    AGENT INSTRUCTIONS:
    • Live (as_of_date=None): calls FMP “stable/biggest-losers” API.
    • Historical (as_of_date set): queries BigQuery table
      `finviz_blacklist.fmp_daily_losers` for scrape_date = as_of_date,
      ordered by changesPercentage ASC, limit=limit.

    Returns a BiggestLosersReport.
    """
    if as_of_date:
        client = bigquery.Client(project="datascience-projects")
        sql = """
          SELECT symbol AS ticker,
                 price,
                 changesPercentage AS change_pct
          FROM `datascience-projects.finviz_blacklist.fmp_daily_losers`
          WHERE scrape_date = @dt
          ORDER BY changesPercentage ASC
          LIMIT @lim
        """
        job = client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("dt", "DATE", as_of_date),
                    bigquery.ScalarQueryParameter("lim", "INT64", limit),
                ]
            )
        )
        losers = [
            MarketLoser(
                ticker=row.ticker,
                price=float(row.price),
                change_pct=float(row.change_pct)
            )
            for row in job.result()
        ]
        return BiggestLosersReport(losers=losers)

    # live path
    api_key = os.environ.get("FMP_API_KEY", "")
    url = f"https://financialmodelingprep.com/stable/biggest-losers?apikey={api_key}"
    try:
        data = requests.get(url).json() or []
        items = data[:limit]
        losers = [
            MarketLoser(
                ticker=item.get("symbol",""),
                price=float(item.get("price",0.0)),
                change_pct=float(item.get("changesPercentage",0.0))
            )
            for item in items
        ]
        return BiggestLosersReport(losers=losers)
    except Exception as e:
        logging.error(f"get_fmp_bigger_losers error: {e}")
        return BiggestLosersReport(losers=[], error_message=str(e))


# -----------------------------------------------------------------------------
# in short_selling_agent/tools.py, overwrite get_fmp_news:

def get_fmp_news(
    ticker: str,
    as_of_date: str | None = None
) -> StockNewsReport:
    """
    Fetch recent news headlines for a ticker, live or for a backtest date.

    AGENT INSTRUCTIONS:
    • Always calls FMP Stock News Feed API:
        https://financialmodelingprep.com/stable/news/stock-latest
      with parameters:
        page=0, limit=50, apikey, and if as_of_date is set, &from=as_of_date&to=as_of_date.
    • Filters returned articles to those whose 'symbol' field matches ticker.
    • Returns up to 10 matching NewsArticle items.
    • If no matches, returns error_message="No news found."
    """
    api_key = os.environ.get("FMP_API_KEY", "")
    base = (
        "https://financialmodelingprep.com/stable/news/stock-latest"
        f"?page=0&limit=50&apikey={api_key}"
    )
    if as_of_date:
        url = f"{base}&from={as_of_date}&to={as_of_date}"
    else:
        url = base

    try:
        data = requests.get(url).json() or []
        # Only keep articles for our ticker
        filtered = [
            item for item in data
            if (item.get("symbol") or "").upper() == (ticker or "").upper()
        ]
        if not filtered:
            return StockNewsReport(
                ticker=ticker, articles=[], error_message="No news found."
            )
        articles = [
            NewsArticle(
                date=item.get("publishedDate",""),
                title=item.get("title","")
            )
            for item in filtered[:10]
        ]
        return StockNewsReport(ticker=ticker, articles=articles)
    except Exception as e:
        logging.error(f"get_fmp_news error: {e}")
        return StockNewsReport(ticker=ticker, articles=[], error_message=str(e))



# -----------------------------------------------------------------------------
def get_bearish_insider_sales(
    ticker: str,
    days_back: int = 180,
    min_value: int = 250_000,
    as_of_date: str | None = None
) -> InsiderTradingReport:
    """
    Fetch insider S-Sales for management.

    AGENT INSTRUCTIONS:
    • Live (as_of_date=None): calls FMP /api/v4/insider-trading.
    • Historical (as_of_date set): queries BQ table `form4_master` for
      filing_date in [as_of_date - days_back, as_of_date], transaction_side='S'.

    Filters (both):
      – transactionType == 'S-Sale'
      – shares*price >= min_value
      – officer_title contains CEO|CFO|COO|PRESIDENT|DIRECTOR

    Returns an InsiderTradingReport.
    """
    if as_of_date:
        client = bigquery.Client(project="datascience-projects")
        sql = """
          SELECT filing_date,
                 owner_name,
                 officer_title,
                 transaction_side,
                 shares,
                 price
          FROM `datascience-projects.gcp_shareloader.form4_master`
          WHERE ticker = @tk
            AND filing_date BETWEEN
                DATE_SUB(@dt, INTERVAL @db DAY) AND @dt
            AND transaction_side = 'S'
        """
        job = client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("tk","STRING",ticker),
                    bigquery.ScalarQueryParameter("dt","DATE",as_of_date),
                    bigquery.ScalarQueryParameter("db","INT64",days_back),
                ]
            ),
        )
        records = list(job.result())
    else:
        api_key = os.environ.get("FMP_API_KEY", "")
        url = (
            f"https://financialmodelingprep.com/api/v4/insider-trading"
            f"?symbol={ticker}&apikey={api_key}"
        )
        try:
            records = requests.get(url).json() or []
        except Exception as e:
            logging.error(f"get_bearish_insider_sales error: {e}")
            return InsiderTradingReport(
                ticker=ticker,
                total_dollars_dumped=0.0,
                significant_sales=[],
                error_message=str(e)
            )

    cutoff = (
        datetime.fromisoformat(as_of_date) if as_of_date else datetime.now()
    ) - timedelta(days=days_back)

    total = 0.0
    sig: list[InsiderTrade] = []
    roles = {"CEO","CFO","COO","PRESIDENT","DIRECTOR"}

    for tr in records:
        # LIVE API dict path
        if isinstance(tr, dict) and "transactionDate" in tr:
            # Only consider S-Sale transactions
            if tr.get("transactionType") != "S-Sale":
                continue

            dt_str = tr.get("transactionDate","")[:10]
            date   = datetime.strptime(dt_str, "%Y-%m-%d").date()
            name   = tr.get("reportingName","")
            title  = str(tr.get("typeOfOwner","")).upper()
            shares = float(tr.get("securitiesTransacted",0) or 0)
            price  = float(tr.get("price",0) or 0)

        else:
            # HISTORICAL BQ row path uses transaction_side='S' in SQL
            date   = tr.filing_date if hasattr(tr, "filing_date") else tr["filing_date"]
            name   = tr.owner_name    if hasattr(tr, "owner_name")   else tr["owner_name"]
            title  = (tr.officer_title or "").upper()             if hasattr(tr, "officer_title") else str(tr["officer_title"]).upper()
            shares = float(tr.shares or 0)                        if hasattr(tr, "shares")       else float(tr["shares"] or 0)
            price  = float(tr.price or 0)                         if hasattr(tr, "price")        else float(tr["price"] or 0)

            # Convert to date if it was a datetime
            if isinstance(date, datetime):
                date = date.date()

        # Skip out-of-window trades
        if date < cutoff.date():
            continue

        value = shares * price
        if value < min_value:
            continue

        if not any(r in title for r in roles):
            continue

        total += value
        sig.append(
            InsiderTrade(
                date=date.isoformat(),
                name=name,
                title=title,
                value_sold=value
            )
        )

    return InsiderTradingReport(
        ticker=ticker,
        total_dollars_dumped=round(total,2),
        significant_sales=sig
    )




# -----------------------------------------------------------------------------
def get_squeeze_metrics(
    ticker: str,
    as_of_date: str | None = None
) -> tuple[float, float]:
    """
    Fetch short interest % and free float.

    AGENT INSTRUCTIONS:
    • Live only (as_of_date=None): calls FMP endpoints.
    • Historical: returns zeros since no historical endpoint.

    Returns: (short_percent_of_float, free_float)
    """
    if as_of_date:
        return 0.0, 0.0

    short_pct  = 0.0
    free_float = 999999999.0
    api_key    = os.environ.get("FMP_API_KEY", "")

    try:
        si = requests.get(
            f"https://financialmodelingprep.com/api/v4/stock-short-interest"
            f"?symbol={ticker}&apikey={api_key}"
        ).json() or []
        if si and isinstance(si, list):
            raw = si[0].get("shortPercentOfFloat")
            short_pct = float(raw) if raw is not None else 0.0

        ff = requests.get(
            f"https://financialmodelingprep.com/api/v4/shares_float"
            f"?symbol={ticker}&apikey={api_key}"
        ).json() or []
        if ff and isinstance(ff, list):
            raw = ff[0].get("freeFloat")
            free_float = float(raw) if raw is not None else free_float

    except Exception as e:
        logging.warning(f"get_squeeze_metrics error: {e}")

    return short_pct, free_float

# -----------------------------------------------------------------------------
# tools/get_bq_short_candidates.py
"""
Fetch top market losers for a given date.
Tries BigQuery first, then falls back to FMP.
"""
# tools/get_bq_short_candidates.py
"""
Low-level BQ helper for losers.
Queries: `datascience-projects.finviz_blacklist.fmp_daily_losers`
"""

import os
import requests
import logging
from google.cloud import bigquery
import datetime
from short_selling_agent.schemas import MarketLoser

# -----------------------------
# Main Tool: fetch big candidates
# -----------------------------
def get_bq_short_candidates(limit: int = 3, as_of_date: str = None):
    """
    AGENT INSTRUCTIONS:
      • Pass as_of_date to query scrape_date = as_of_date,
        otherwise DEFAULT to CURRENT_DATE().
      • Returns List[MarketLoser] with ticker, price, change_pct.
      • Uses `datascience-projects.finviz_blacklist.fmp_daily_losers`
    """
    table_ref = "datascience-projects.finviz_blacklist.fmp_daily_losers"

    # Choose date
    if as_of_date:
        query_date = as_of_date  # "YYYY-MM-DD"
    else:
        # Default to yesterday
        query_date = (
            datetime.datetime.now().date() - datetime.timedelta(days=1)
        ).isoformat()

    return _fetch_from_bigquery(table_ref, limit, query_date)


# -----------------------------
# 1. Fetch from BigQuery
# -----------------------------
def _fetch_from_bigquery(table_ref: str, limit: int, query_date: str):
    """
    Load big losers where `scrape_date` = query_date
    Schema:
        scrape_date DATE
        ticker STRING
        currentPrice FLOAT
        change FLOAT  → e.g., -0.145 for -14.5%
    """
    project_id = os.environ.get("GCP_PROJECT_ID", "datascience-projects")
    client = bigquery.Client()

    query = f"""
        SELECT
            ticker,
            currentPrice AS price,
            change * 100 AS change_pct  -- to percent (-0.145 → -14.5)
        FROM `{table_ref}`
        WHERE DATE(scrape_date) = @target_date  -- Aligns with as_of_date
        AND change < 0
        ORDER BY change ASC
        LIMIT {limit}
    """

    try:
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("target_date", "DATE", query_date)
            ]
        )

        rows = client.query(query, job_config=job_config).result()

        return [
            MarketLoser(
                ticker=row["ticker"].strip(),
                price=row["price"],
                change_pct=round(row["change_pct"], 1)
            )
            for row in rows
        ]

    except Exception as e:
        logging.error(f"❌ BQ fetch failed: {e}")
        return None


# -----------------------------
# 2. Fallback: FMP - Earnings Miss + Drop
# -----------------------------
def _fetch_from_fmp_approx(target_date: str, limit: int) -> list:
    """
    Fallback: Use FMP earnings calendar to get big decliners.
    """
    FMP_KEY = os.getenv('FMP_API_KEY')
    if not FMP_KEY:
        return []

    try:
        url = (
            f"https://financialmodelingprep.com/api/v4/earning_calendar"
            f"?from={target_date}&to={target_date}&apikey={FMP_KEY}"
        )
        resp = requests.get(url, timeout=10)
        if resp.status_code != 200:
            return []

        earnings = resp.json()
        losers = []

        for e in earnings:
            ticker = e.get("ticker")
            close_price = e.get("close", 0)
            change = e.get("percentage", 0)  # in % (e.g., -12.3)

            if change < -10.0:  # big drop
                losers.append(
                    MarketLoser(
                        ticker=ticker,
                        price=close_price,
                        change_pct=round(change, 1)
                    )
                )
                if len(losers) >= limit:
                    break

        return losers

    except Exception as e:
        logging.error(f"🔴 FMP fallback error: {e}")
        return []


# -----------------------------
# Final Public Function
# -----------------------------
# Already defined up top: `get_bq_short_candidates(...)`
