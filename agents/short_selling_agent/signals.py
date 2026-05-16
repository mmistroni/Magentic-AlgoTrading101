# signals.py
"""
Short Signal Generator
Generates historical short-sell candidates using:
  1. BigQuery: primary source (fmp_daily_losers)
  2. FMP earning_calendar: fallback for EOD big drops

Only runs within 1-year window (required by FMP plan).
"""

import os
import logging
import requests
from datetime import datetime, timedelta
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import your tools
import short_selling_agent.tools as tools
from short_selling_agent.tools import get_bq_short_candidates


# -------------------------------
# 🔧 Config
# -------------------------------
FALLBACK_DAYS = 2  # ±2 days around date for earnings
RECENT_WEEKS = 12  # Only look back 3 months to stay in FMP 1-year window
DATE_FORMAT = "%Y-%m-%d"


def generate_backtest_dates(num_weeks: int = RECENT_WEEKS) -> List[str]:
    """
    Generate a list of Fridays from N weeks back to now.
    Helps anchor weekly signal generation.
    """
    today = datetime.now()
    start = today - timedelta(weeks=num_weeks)
    dates = []
    current = start

    while current.date() <= today.date():
        if current.weekday() == 4:  # Friday
            dates.append(current.strftime(DATE_FORMAT))
        current += timedelta(days=1)
    return dates


def run_signal_pipeline():
    """
    Main signal generation loop:
    • Iterates through recent Fridays
    • Tries BQ first
    • Falls back to FMP earning_calendar
    • Tracks missing data
    """
    dates = generate_backtest_dates()
    logger.info(f"🚀 Starting short-signal generation on {len(dates)} backtest dates...")

    for target_date in dates:
        logger.info(f"\n📅 Processing date: {target_date}")

        try:
            # 🧱 Primary: BQ → with fallback
            candidates = get_bq_short_candidates(limit=5, as_of_date=target_date)

            if candidates:
                tickers = [c["ticker"] for c in candidates]
                prices = [c["price"] for c in candidates]
                logger.info(f"  ✅ Signal: {tickers}")
            else:
                logger.warning(f"  ⚠️ No tickers for {target_date}")

        except Exception as e:
            logger.error(f"❌ Error processing {target_date}: {e}")

    logger.info("\n🎯 Signal generation complete. Review output above.")


# -------------------------------
# 🧪 Test FMP Fallback (Optional)
# -------------------------------
def test_fallback_single_date(date: str):
    """
    Test fallback for one date. For debugging only.
    """
    logger.info(f"🧪 Testing fallback for {date}")
    from short_selling_agent.tools import _fetch_from_fmp_earning_drop_fallback
    result = _fetch_from_fmp_earning_drop_fallback(date, limit=5)
    if result:
        print("🎯 Found:", [(r.ticker, f"{r.change_pct:.1%}") for r in result])
    else:
        print("❌ No big drops found (check FMP access or date range).")


# -------------------------------
# 🚀 Run Script
# -------------------------------
if __name__ == "__main__":
    # 🔁 Generate and run on last 12 weeks only
    run_signal_pipeline()

    # 💡 Optional: Test fallback directly
    # test_fallback_single_date("2025-04-01")