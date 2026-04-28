# short_selling_agent/tools.py

from .finviz_tools import get_short_squeeze_filter
from .schemas import (
    BiggestLosersReport,
    MarketLoser,
    StockNewsReport,
    NewsArticle,
    InsiderTradingReport,
    InsiderTrade,
)
import logging
import requests
import os
from datetime import datetime, timedelta
from google.cloud import bigquery


# -----------------------------------------------------------------------------
def get_fmp_bigger_losers(
    as_of_date: str | None = None
) -> BiggestLosersReport:
    """
    Fetches the biggest market losers for a given date.

    AGENT INSTRUCTIONS:
      • If `as_of_date` is None: calls the live FMP “biggest-losers” endpoint
        and returns today’s losers.
      • If `as_of_date` is a string "YYYY-MM-DD": 
          – delegates to your historical BQ table via get_bq_short_candidates()
          – wraps those rows in MarketLoser objects and returns a BiggestLosersReport.
    
    Example:
      # live (today)
      get_fmp_bigger_losers()
    
      # historical (June 1, 2023)
      get_fmp_bigger_losers(as_of_date="2023-06-01")
    """
    # Historical path: use your BigQuery ingestion table
    if as_of_date:
        rows = get_bq_short_candidates(limit=10, as_of_date=as_of_date)
        losers = [
            MarketLoser(
                ticker=r["ticker"],
                price=r["price"],
                change_pct=r["change_pct"]
            )
            for r in rows
        ]
        return BiggestLosersReport(losers=losers)

    # Live path: FinancialModelingPrep API
    api_key = os.environ.get("FMP_API_KEY", "")
    url = (
        f"https://financialmodelingprep.com/stable/biggest-losers"
        f"?apikey={api_key}"
    )
    try:
        data = requests.get(url).json()
        losers = [
            MarketLoser(
                ticker=item.get("symbol", ""),
                price=float(item.get("price", 0.0)),
                change_pct=float(item.get("changesPercentage", 0.0)),
            )
            for item in data or []
        ]
        return BiggestLosersReport(losers=losers)
    except Exception as e:
        logging.error(f"Failed to retrieve biggest losers: {e}")
        return BiggestLosersReport(losers=[], error_message=str(e))


# -----------------------------------------------------------------------------
def get_fmp_news(
    ticker: str,
    as_of_date: str | None = None
) -> StockNewsReport:
    """
    Fetches recent news for a stock, live or historical.

    AGENT INSTRUCTIONS:
      • For real-time use (`as_of_date=None`), calls the FMP stock-news API.
      • For backtests (`as_of_date="YYYY-MM-DD"`), queries your BQ table:
          your_project.historical_news(
            ticker STRING,
            publishedDate TIMESTAMP,
            title STRING
          )
    
    Returns:
      StockNewsReport(ticker, List[NewsArticle], optional error_message)
    """
    if as_of_date:
        client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID"))
        sql = """
          SELECT publishedDate, title
          FROM `your_project.historical_news`
          WHERE ticker = @ticker
            AND DATE(publishedDate) = @dt
          ORDER BY publishedDate DESC
          LIMIT 10
        """
        job = client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
                    bigquery.ScalarQueryParameter("dt", "DATE", as_of_date),
                ]
            ),
        )
        rows = list(job.result())
        if not rows:
            return StockNewsReport(
                ticker=ticker,
                articles=[],
                error_message="No historical news for that date."
            )
        articles = [
            NewsArticle(date=row.publishedDate.isoformat(), title=row.title)
            for row in rows
        ]
        return StockNewsReport(ticker=ticker, articles=articles)

    # Live API path
    api_key = os.environ.get("FMP_API_KEY", "")
    url = (
        f"https://financialmodelingprep.com/api/v3/stock-news"
        f"?tickers={ticker}&limit=10&apikey={api_key}"
    )
    try:
        data = requests.get(url).json() or []
        if not data:
            return StockNewsReport(ticker=ticker, articles=[], error_message="No news found.")
        articles = [
            NewsArticle(
                date=item.get("publishedDate", ""),
                title=item.get("title", ""),
            )
            for item in data
        ]
        return StockNewsReport(ticker=ticker, articles=articles)
    except Exception as e:
        logging.error(f"Error FMP News API: {e}")
        return StockNewsReport(ticker=ticker, articles=[], error_message=str(e))


# -----------------------------------------------------------------------------
def get_bearish_insider_sales(
    ticker: str,
    days_back: int = 180,
    min_value: int = 250_000,
    as_of_date: str | None = None
) -> InsiderTradingReport:
    """
    Fetches C-Suite SEC Form 4 insider sales, live or historical.

    AGENT INSTRUCTIONS:
      • For real-time (`as_of_date=None`):
          calls FMP insider-trading API.
      • For backtest (`as_of_date="YYYY-MM-DD"`):
          queries your BQ table:
            your_project.historical_form4(
              symbol STRING,
              transactionDate TIMESTAMP,
              transactionType STRING,
              securitiesTransacted FLOAT,
              price FLOAT,
              typeOfOwner STRING,
              reportingName STRING
            )
          and filters for:
            – transactionType = 'S-Sale'
            – within `days_back` of as_of_date
            – dollar value ≥ `min_value`
            – owner titles in [CEO, CFO, COO, PRESIDENT, DIRECTOR]

    Returns:
      InsiderTradingReport(ticker, total_dollars_dumped, List[InsiderTrade], optional error_message)
    """
    if as_of_date:
        client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID"))
        sql = """
          SELECT
            transactionDate,
            transactionType,
            securitiesTransacted,
            price,
            typeOfOwner,
            reportingName
          FROM `your_project.historical_form4`
          WHERE symbol = @ticker
            AND DATE(transactionDate) >= DATE_SUB(@dt, INTERVAL @db DAY)
        """
        job = client.query(
            sql,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("ticker", "STRING", ticker),
                    bigquery.ScalarQueryParameter("dt", "DATE", as_of_date),
                    bigquery.ScalarQueryParameter("db", "INT64", days_back),
                ]
            ),
        )
        data = list(job.result())
    else:
        api_key = os.environ.get("FMP_API_KEY", "")
        url = (
            f"https://financialmodelingprep.com/api/v4/insider-trading"
            f"?symbol={ticker}&apikey={api_key}"
        )
        try:
            data = requests.get(url).json() or []
            if not isinstance(data, list):
                data = []
        except Exception as e:
            logging.error(f"Error Form4 API: {e}")
            return InsiderTradingReport(
                ticker=ticker,
                total_dollars_dumped=0.0,
                significant_sales=[],
                error_message=str(e)
            )

    cutoff = (
        datetime.fromisoformat(as_of_date) if as_of_date else datetime.now()
    ) - timedelta(days=days_back)

    total_dumped = 0.0
    significant_sales: list[InsiderTrade] = []
    target_roles = {'CEO','CFO','COO','PRESIDENT','DIRECTOR'}

    for trade in data:
        dt_str = trade.get("transactionDate", "")[:10]
        if trade.get("transactionType") != "S-Sale":
            continue
        tx_dt = datetime.strptime(dt_str, "%Y-%m-%d")
        if tx_dt < cutoff:
            continue

        shares = float(trade.get("securitiesTransacted", 0) or 0)
        price  = float(trade.get("price", 0) or 0)
        value  = shares * price
        if value < min_value:
            continue

        owner = str(trade.get("typeOfOwner", "")).upper()
        if not any(role in owner for role in target_roles):
            continue

        total_dumped += value
        significant_sales.append(
            InsiderTrade(
                date=dt_str,
                name=trade.get("reportingName", ""),
                title=owner,
                value_sold=value,
            )
        )

    return InsiderTradingReport(
        ticker=ticker,
        total_dollars_dumped=round(total_dumped, 2),
        significant_sales=significant_sales
    )


# -----------------------------------------------------------------------------
def get_squeeze_metrics(
    ticker: str,
    as_of_date: str | None = None
) -> tuple[float, float]:
    """
    Fetches short‐interest % and free float, live or historical.

    AGENT INSTRUCTIONS:
      • For real-time (`as_of_date=None`):
          calls FMP endpoints:
            – /api/v4/stock-short-interest
            – /api/v4/shares_float
      • For backtest (`as_of_date="YYYY-MM-DD"`):
          queries your BQ tables:
            historical_stock_short_interest(symbol, date, shortPercentOfFloat)
            historical_shares_float(symbol, date, freeFloat)
          and returns that row’s values.

    Returns: (short_pct: float, free_float: float)
    """
    if as_of_date:
        client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID"))
        # Query short interest
        sql1 = """
          SELECT shortPercentOfFloat
          FROM `your_project.historical_stock_short_interest`
          WHERE symbol=@ticker AND date=@dt
          LIMIT 1
        """
        job1 = client.query(
            sql1,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("ticker","STRING",ticker),
                    bigquery.ScalarQueryParameter("dt","DATE",as_of_date),
                ]
            )
        )
        rec1 = list(job1.result())
        short_pct = float(rec1[0].shortPercentOfFloat or 0.0) if rec1 else 0.0

        # Query free float
        sql2 = """
          SELECT freeFloat
          FROM `your_project.historical_shares_float`
          WHERE symbol=@ticker AND date=@dt
          LIMIT 1
        """
        job2 = client.query(
            sql2,
            job_config=bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("ticker","STRING",ticker),
                    bigquery.ScalarQueryParameter("dt","DATE",as_of_date),
                ]
            )
        )
        rec2 = list(job2.result())
        free_float = float(rec2[0].freeFloat or 0.0) if rec2 else 0.0

        return short_pct, free_float

    # Live API path
    short_pct = 0.0
    free_float = 999_999_999.0
    try:
        key = os.environ["FMP_API_KEY"]
        # 1) short interest
        si = requests.get(
            f"https://financialmodelingprep.com/api/v4/stock-short-interest"
            f"?symbol={ticker}&apikey={key}"
        ).json() or []
        if si and isinstance(si, list):
            raw = si[0].get("shortPercentOfFloat")
            short_pct = float(raw) if raw is not None else 0.0

        # 2) free float
        ff = requests.get(
            f"https://financialmodelingprep.com/api/v4/shares_float"
            f"?symbol={ticker}&apikey={key}"
        ).json() or []
        if ff and isinstance(ff, list):
            raw = ff[0].get("freeFloat")
            free_float = float(raw) if raw is not None else free_float

    except Exception as e:
        logging.warning(f"Failed to fetch squeeze metrics for {ticker}: {e}")

    return short_pct, free_float


# -----------------------------------------------------------------------------
def get_bq_short_candidates(
    limit: int = 3,
    as_of_date: str | None = None
) -> list[dict]:
    """
    Fetches the top dropping stocks from your BigQuery ingestion table.

    AGENT INSTRUCTIONS:
      • To backtest a historical date, pass `as_of_date="YYYY-MM-DD"`.
      • If omitted, defaults to CURRENT_DATE().
      • Returns a list of dicts with keys:
          ticker, price, change_pct, short_interest_pct, free_float, is_squeeze_risk.

    Example:
      get_bq_short_candidates(limit=5, as_of_date="2023-06-01")
    """
    client = bigquery.Client(project="datascience-projects")
    if as_of_date:
        date_filter = f"DATE '{as_of_date}'"
    else:
        date_filter = "CURRENT_DATE()"

    sql = f"""
      SELECT
        ticker,
        price,
        change_pct,
        short_interest_pct,
        free_float,
        is_squeeze_risk
      FROM `datascience-projects.finviz_blacklist.fmp_daily_losers`
      WHERE scrape_date = {date_filter}
        AND price >= 5.0
      ORDER BY change_pct ASC
      LIMIT @limit
    """
    job = client.query(
        sql,
        job_config=bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("limit", "INT64", limit),
            ]
        ),
    )
    return [dict(row) for row in job.result()]