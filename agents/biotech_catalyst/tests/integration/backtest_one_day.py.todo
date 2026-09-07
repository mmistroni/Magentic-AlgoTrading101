import os
import argparse
import datetime
import pandas as pd
from google.cloud import bigquery

# reuse your tools
from short_selling_agent.tools import get_squeeze_metrics, get_fmp_news, get_bearish_insider_sales
from short_selling_agent.schemas import MarketLoser

def fetch_candidates(as_of_date: datetime.date, limit: int=5):
    """
    Query your fmp_daily_losers table for that date.
    """
    client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID"))
    sql = """
      SELECT ticker, price, change_pct
      FROM `datascience-projects.finviz_blacklist.fmp_daily_losers`
      WHERE scrape_date = @dt
        AND price >= 5.0
      ORDER BY change_pct ASC
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
    rows = job.result()
    return [ MarketLoser(ticker=r.ticker, price=r.price, change_pct=r.change_pct) for r in rows ]


def fetch_exit_prices(as_of_date: datetime.date, tickers: list[str], hold_days: int):
    """
    Query your daily prices table to get the price 'hold_days' after as_of_date.
    """
    exit_date = as_of_date + datetime.timedelta(days=hold_days)
    client = bigquery.Client(project=os.environ.get("GCP_PROJECT_ID"))
    sql = """
      SELECT ticker, close
      FROM `datascience-projects.finviz_blacklist.fmp_daily_prices`
      WHERE date = @dt
        AND ticker IN UNNEST(@tks)
    """
    job = client.query(
      sql,
      job_config=bigquery.QueryJobConfig(
        query_parameters=[
          bigquery.ScalarQueryParameter("dt", "DATE", exit_date),
          bigquery.ArrayQueryParameter("tks", "STRING", tickers),
        ]
      )
    )
    return { row.ticker: row.close for row in job.result() }


def backtest_date(as_of_str: str, limit: int=5, hold_days: int=2):
    as_of = datetime.date.fromisoformat(as_of_str)
    print(f"\nBacktesting date: {as_of}  (limit={limit}, hold_days={hold_days})\n")

    # 1) Fetch that day’s losers
    losers = fetch_candidates(as_of, limit)
    print("Candidates:", [m.ticker for m in losers])

    # 2) Compute signals
    trades = []
    for m in losers:
        short_pct, free_float = get_squeeze_metrics(m.ticker)
        news_rpt = get_fmp_news(m.ticker)
        ins_rpt = get_bearish_insider_sales(m.ticker)
        # example rule: SHORT if >20% short interest OR >\$1M insider dump
        action = "SHORT" if (short_pct > 20 or ins_rpt.total_dollars_dumped > 1e6) else "AVOID"
        trades.append({
            "ticker": m.ticker,
            "entry_price": m.price,
            "short_pct": short_pct,
            "insider_dump": ins_rpt.total_dollars_dumped,
            "action": action
        })

    df = pd.DataFrame(trades)
    print("\nSignals:")
    print(df[["ticker","action","short_pct","insider_dump"]])

    # 3) Fetch exit prices, compute PnL for SHORTs
    exit_map = fetch_exit_prices(as_of, df["ticker"].tolist(), hold_days)
    df["exit_price"] = df["ticker"].map(exit_map)
    df["return_pct"] = df.apply(
        lambda r: (r.entry_price - r.exit_price) / r.entry_price
                  if (r.action=="SHORT" and pd.notna(r.exit_price)) else 0.0,
        axis=1
    )

    print(f"\nResults (hold {hold_days} days):")
    print(df[["ticker","action","entry_price","exit_price","return_pct"]])
    print("\nAvg return:", df["return_pct"].mean())
    print("Win rate:", (df["return_pct"]>0).mean())

if __name__=="__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", required=True,
        help="Backtest date in YYYY-MM-DD format")
    parser.add_argument("--limit", type=int, default=5,
        help="How many top losers to test")
    parser.add_argument("--hold-days", type=int, default=2,
        help="Days to hold the short")
    args = parser.parse_args()

    # ensure your env vars are set:
    #   export GCP_PROJECT_ID=…    export FMP_API_KEY=…
    backtest_date(args.date, limit=args.limit, hold_days=args.hold_days)