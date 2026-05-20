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
# -----------------------------------------------------------------------------
def get_fmp_bigger_losers(
    limit: int = 5,
    as_of_date: str | None = None
) -> BiggestLosersReport:
    """
    Fetch biggest losers with fallback only for historical dates.

    • Live (as_of_date=None): Use FMP's /stable/biggest-losers
    • Historical (as_of_date=YYYY-MM-DD):
        1. Try BigQuery `fmp_daily_losers`
        2. If empty, fall back to FMP earning_calendar
        3. If both fail → error
    """
    # ———————————————————————————————————
    # Case A: Historical Request → BQ + Fallback
    # ———————————————————————————————————
    print(f"🔍 [get_fmp_bigger_losers] Starting fetch: as_of_date={as_of_date}, limit={limit}")
    if as_of_date:
        logging.info(f"🔍 [get_fmp_bigger_losers] Historical mode: fetching losers for {as_of_date}, limit={limit}")

        try:
            client = bigquery.Client(project="datascience-projects")
            sql = """
                SELECT ticker, price, change_pct, short_interest_pct, free_float, is_squeeze_risk
                FROM `datascience-projects.finviz_blacklist.fmp_daily_losers`
                WHERE scrape_date >= TIMESTAMP(@dt)
                    AND scrape_date < TIMESTAMP_ADD(TIMESTAMP(@dt), INTERVAL 1 DAY)
                    AND price >= 5.0
                    AND change_pct IS NOT NULL
                ORDER BY change_pct ASC
                LIMIT @lim
                """
            job_config = bigquery.QueryJobConfig(
                query_parameters=[
                    bigquery.ScalarQueryParameter("dt", "DATE", as_of_date),
                    bigquery.ScalarQueryParameter("lim", "INT64", limit),
                ]
            )
            job = client.query(sql, job_config=job_config)
            rows = list(job.result())  # Force execution
            logging.info(f"📊 BQ query completed: {len(rows)} row(s) returned")

            losers = [
                MarketLoser(
                    ticker=row.ticker,
                    price=float(row.price),
                    change_pct=float(row.change_pct)
                )
                for row in rows
            ]

            if losers:
                logging.info(f"✅ BQ success: {len(losers)} losers: {[l.ticker for l in losers]}")
                return BiggestLosersReport(losers=losers)

        except Exception as e:
            logging.error(f"❌ BQ query failed for {as_of_date}: {e}")

        # ———————— Fallback: earning_calendar ————————
        logging.warning(f"📡 [FALLBACK] No data from BQ for {as_of_date} → trying FMP earning_calendar")
        try:
            fmp_fallback = _fetch_from_fmp_earning_drop_fallback(as_of_date, limit)
            if fmp_fallback:
                logging.info(f"✅ Fallback succeeded: {len(fmp_fallback)} losers: {[l.ticker for l in fmp_fallback]}")
                return BiggestLosersReport(losers=fmp_fallback)
            else:
                logging.info(f"❌ Fallback returned 0 losers for {as_of_date}")
        except Exception as e:
            logging.error(f"💥 FMP fallback failed: {e}")

        # ———————— Final: Nothing worked ————————
        error_msg = f"⚠️ No market losers found for {as_of_date} via BQ or FMP fallback"
        logging.warning(error_msg)
        return BiggestLosersReport(losers=[], error_message=error_msg)

    # ———————————————————————————————————
    # Case B: Live Request → Use FMP Real-Time API
    # ———————————————————————————————————
    api_key = os.environ.get("FMP_API_KEY", "")
    if not api_key:
        error_msg = "FMP_API_KEY missing"
        logging.error(error_msg)
        return BiggestLosersReport(losers=[], error_message=error_msg)

    url = f"https://financialmodelingprep.com/stable/biggest-losers?apikey={api_key}"
    logging.info("🚀 [Live] Fetching biggest losers from FMP")
    try:
        response = requests.get(url, timeout=10)
        logging.debug(f"📡 FMP response status: {response.status_code}")

        if response.status_code != 200:
            logging.warning(f"❌ FMP /biggest-losers returned {response.status_code}: {response.text[:200]}")
            return BiggestLosersReport(losers=[], error_message=f"HTTP {response.status_code}")

        data = response.json()
        if not isinstance(data, list):
            logging.warning(f"⚠️ FMP /biggest-losers did not return a list: got {type(data)}")
            return BiggestLosersReport(losers=[], error_message="Invalid response format")

        items = data[:limit]
        losers = [
            MarketLoser(
                ticker=item.get("symbol", ""),
                price=float(item.get("price", 0.0)),
                change_pct=float(item.get("changesPercentage", 0.0)) / 100.0
                if item.get("changesPercentage") not in (None, "") else 0.0
            )
            for item in items
            if item.get("symbol")
        ]

        logging.info(f"✅ Live mode: {len(losers)} losers fetched: {[l.ticker for l in losers]}")
        return BiggestLosersReport(losers=losers)

    except Exception as e:
        logging.error(f"💥 Error in live biggest-losers fetch: {e}")
        return BiggestLosersReport(losers=[], error_message=str(e))

# -----------------------------------------------------------------------------
# in short_selling_agent/tools.py, overwrite get_fmp_news:

def get_fmp_news(
    ticker: str,
    as_of_date: str = ''
) -> StockNewsReport:
    """
    Fetches historical or live institutional newsheadlines, catalysts, and coverage feeds for an equity ticker.

    AGENT INSTRUCTIONS:
    • Calls the FMP Stock News Feed API endpoint:
        https://financialmodelingprep.com/stable/news/stock-latest
      with required parameters: page=0, limit=50, and apikey.
    • Historical Scoping Mode (as_of_date is provided): Dynamically builds a trailing 3-day 
      window (&from=as_of_date-3&to=as_of_date) to prevent calendar date context gaps.
    • Live Scoping Mode (as_of_date is ''): Pulls global real-time streams.
    • Post-Filter Constraints: Scans the array payload and filters records matching 
      the targeted uppercase 'symbol' property.
    • Outputs a truncated collection mapping up to 10 strict NewsArticle schemas.

    Args:
        ticker (str): Capitalized market asset symbol string (e.g., 'NVDA', 'AAPL').
        as_of_date (str, optional): Target observation baseline formatted as 'YYYY-MM-DD'. 
            Defaults to an empty string '' for real-time streaming lookups.

    Returns:
        StockNewsReport: Data payload containment object tracking filtered NewsArticle records 
            mapping publication dates and titles. Supplies an explicit error_message string if empty.
    """
    api_key = os.environ.get("FMP_API_KEY", "")
    # 🛠️ FIX: Target the symbol endpoint directly so FMP returns articles ONLY for this ticker
    base = (
        f"https://financialmodelingprep.com/stable/news/stock-latest"
        f"?symbol={ticker.upper()}&page=0&limit=10&apikey={api_key}"
    )
    
    if as_of_date:
        try:
            end_dt = datetime.strptime(as_of_date, "%Y-%m-%d")
            start_dt = end_dt - timedelta(days=3)
            from_str = start_dt.strftime("%Y-%m-%d")
            # Appends the trailing parameters safely
            url = f"{base}&from={from_str}&to={as_of_date}"
        except Exception:
            url = f"{base}&from={as_of_date}&to={as_of_date}"
    else:
        url = base

    # 🔬 DEBUG ASSISTANCE: Print statement to immediately copy-paste the URL out of Codespaces
    print(f"🚀 [DEBUG URL] get_fmp_news executing network fetch via:\n{url}")

    try:
        response = requests.get(url, timeout=10)
        
        # Guard against bad HTTP responses completely
        if response.status_code != 200:
            error_msg = f"HTTP {response.status_code}: {response.text[:100]}"
            return StockNewsReport(ticker=ticker, articles=[], error_message=error_msg)
            
        data = response.json() or []
        
        # Guard against non-list structures (error dict responses from FMP)
        if not isinstance(data, list):
            return StockNewsReport(
                ticker=ticker, 
                articles=[], 
                error_message=f"FMP endpoint returned invalid response type layout: {str(data)[:100]}"
            )

        # Explicit type validation loop to step around the 'NoneType' crash
        filtered = []
        for item in data:
            if isinstance(item, dict) and item.get("symbol"):
                if str(item.get("symbol")).upper() == ticker.upper():
                    filtered.append(item)

        if not filtered:
            return StockNewsReport(
                ticker=ticker, articles=[], error_message="No news found."
            )
            
        articles = [
            NewsArticle(
                date=str(item.get("publishedDate") or ""),
                title=str(item.get("title") or "")
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
def get_bq_short_candidates(
    limit: int = 5,
    as_of_date: str | None = None
) -> list[dict]:
    """
    Fetch top EOD losers:
      - Try BigQuery fmp_daily_losers first
      - If empty/fail → fall back to FMP earning_calendar

    Returns list of dicts with:
      {ticker, price, change_pct, short_interest_pct, free_float, is_squeeze_risk}
    """
    # Determine date
    if as_of_date:
        query_date = as_of_date
    else:
        query_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    logging.info(f"🔍 [get_bq_short_candidates] Fetching for date={query_date}, limit={limit}")

    # -------------------------------
    # Step 1: Try BigQuery
    # -------------------------------
    try:
        client = bigquery.Client(project="datascience-projects")
        sql = """
          SELECT ticker, price, change_pct, short_interest_pct, free_float, is_squeeze_risk
          FROM `datascience-projects.finviz_blacklist.fmp_daily_losers`
          WHERE DATE(scrape_date) = @dt
            AND price >= 5.0
            AND change_pct IS NOT NULL
          ORDER BY change_pct ASC
          LIMIT @lim
        """
        print(f'Executing query:\n{sql}')
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("dt", "DATE", query_date),
                bigquery.ScalarQueryParameter("lim", "INT64", limit),
            ]
        )
        # 🛠️ FIX: Construct a dry-run preview string to see what is actually happening
        executed_sql_preview = sql.replace("@dt", f"'{query_date}'").replace("@lim", str(limit))
        print(f'Executing query:\n{executed_sql_preview}')

        job = client.query(sql, job_config=job_config)
        rows = list(job.result())

        if rows:
            result = [dict(row) for row in rows]
            logging.info(f"✅ BQ success: {len(result)} tickers = {[r['ticker'] for r in result]}")
            return result
        else:
            logging.warning(f"⚠️ BQ returned no data for {query_date} and sql \n {sql}")

    except Exception as e:
        logging.error(f"❌ BQ query failed: {e}")

    # -------------------------------
    # Step 2: Fall back to FMP earning_calendar
    # -------------------------------
    logging.warning(f"📡 [FALLBACK] No BQ data for {query_date} → falling back to FMP earning_calendar")
    try:
        fmp_losers = _fetch_from_fmp_earning_drop_fallback(query_date, limit)
        if fmp_losers:
            # Convert to dict format; fill missing S/Risk fields with default
            result = [
                {
                    "ticker": ml.ticker,
                    "price": ml.price,
                    "change_pct": ml.change_pct,
                    "short_interest_pct": 0.0,
                    "free_float": 0.0,
                    "is_squeeze_risk": False,
                }
                for ml in fmp_losers
            ]
            logging.info(f"✅ Fallback success: {len(result)} tickers = {[r['ticker'] for r in result]}")
            return result
        else:
            logging.info(f"❌ FMP fallback returned no data for {query_date}")

    except Exception as e:
        logging.error(f"💥 FMP fallback failed: {e}")

    # -------------------------------
    # Final: Nothing worked
    # -------------------------------
    logging.warning(f"🛑 No candidates found for {query_date}")
    return []


# -----------------------------------------------------------------------------
def _fetch_from_fmp_earning_drop_fallback(target_date: str, limit: int = 5) -> list[MarketLoser]:
    """
    Internal utility to extract high-magnitude historical price drop events using FMP's 
    earning_calendar dataset endpoints. Executed as a fallback pipeline mechanism when 
    the native primary BigQuery data frames return blank.

    Updates: Now scans a trailing 7-day window leading up to target_date instead of a single day.
    """
    FMP_KEY = os.environ.get("FMP_API_KEY")
    if not FMP_KEY:
        logging.error("❌ FMP_API_KEY not set in _fetch_from_fmp_earning_drop_fallback")
        return []

    # 1. Parse the target execution date
    try:
        end_dt = datetime.strptime(target_date, "%Y-%m-%d")
    except ValueError:
        logging.error(f"❌ Invalid target_date format: '{target_date}'. Defaulting to today.")
        end_dt = datetime.now()

    # 2. Compute a trailing 7-day starting boundary
    start_dt = end_dt - timedelta(days=7)
    
    from_date = start_dt.strftime("%Y-%m-%d")
    to_date = end_dt.strftime("%Y-%m-%d")

    # 3. Target FMP earning_calendar using the date range parameters
    url = (
        f"https://financialmodelingprep.com/api/v4/earning_calendar"
        f"?from={from_date}&to={to_date}&apikey={FMP_KEY}"
    )
    logging.info(f"📡 [FMP Fallback] Scanning 7-day window: from={from_date} to={to_date}")

    try:
        response = requests.get(url, timeout=10)
        if response.status_code != 200:
            logging.warning(f"❌ [FMP Fallback] Bad status: {response.status_code}")
            return []

        data = response.json()
        if not isinstance(data, list):
            logging.warning(f"⚠️ [FMP Fallback] Expected list, got: {type(data)}")
            return []

        losers = []
        for e in data:
            ticker = str(e.get("ticker") or "").strip()
            if not ticker:
                continue
            
            close_price = float(e.get("close") or 0.0)
            change_pct_raw = float(e.get("percentage") or 0.0)
            change_pct = change_pct_raw / 100.0

            # Filter for significant setups (>10% drops)
            if change_pct < -0.10:
                losers.append(
                    MarketLoser(ticker=ticker, price=close_price, change_pct=change_pct)
                )

        # Sort absolute worst performers first across the whole week
        losers.sort(key=lambda x: x.change_pct)
        
        # Deduplicate by ticker in case a symbol appears multiple times in the calendar feed
        seen = set()
        deduped_losers = []
        for loser in losers:
            if loser.ticker not in seen:
                seen.add(loser.ticker)
                deduped_losers.append(loser)

        logging.info(f"🎯 [FMP Fallback] Found {len(deduped_losers)} unique big-drop stocks over the past week.")
        return deduped_losers[:limit]

    except Exception as e:
        logging.error(f"💥 [FMP Fallback] Exception: {e}")
        return []