import os
import json
import logging
import requests
from datetime import datetime, timedelta
from typing import List

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Import your tools safely from your package space
try:
    import short_selling_agent.tools as tools
    from short_selling_agent.tools import get_bq_short_candidates
except ImportError:
    get_bq_short_candidates = None

# -------------------------------
# 🔧 Config
# -------------------------------
RECENT_WEEKS = 12  # Looks back 3 months (Perfectly fits inside FMP's 1-year window)
DATE_FORMAT = "%Y-%m-%d"


def generate_daily_backtest_dates(num_weeks: int = RECENT_WEEKS) -> List[str]:
    """
    Generate a sequential list of ALL weekdays over the window.
    Strictly includes only Mondays, Tuesdays, and Wednesdays to prevent weekend holding risk.
    """
    today = datetime.now()
    start = today - timedelta(weeks=num_weeks)
    dates = []
    current = start

    while current.date() <= today.date():
        # 0: Monday, 1: Tuesday, 2: Wednesday
        if current.weekday() in [0, 1, 2]:
            dates.append(current.strftime(DATE_FORMAT))
        current += timedelta(days=1)
    return dates


def run_signal_pipeline():
    """
    Main daily signal generation pipeline.
    Queries your BigQuery structure day-by-day to capture true daily momentum.
    """
    dates = generate_daily_backtest_dates()
    logger.info(f"🚀 Starting DAILY short-signal generation across {len(dates)} safe weekdays...")
    
    all_extracted_signals = []

    for target_date in dates:
        logger.info(f"📅 Scanning Date: {target_date}")

        if get_bq_short_candidates is None:
            logger.error("❌ short_selling_agent tools are not available in your current environment.")
            return

        try:
            # Fetch candidates for this specific weekday from BigQuery
            candidates = get_bq_short_candidates(limit=5, as_of_date=target_date)

            if candidates:
                tickers = [c["ticker"] for c in candidates]
                logger.info(f"  ✅ Signals Found: {tickers}")
                
                # Format and append to our master list
                for c in candidates:
                    all_extracted_signals.append({
                        "ticker": c["ticker"],
                        "date": target_date,
                        "price": c.get("price"),
                        "conviction_score": c.get("conviction_score", 8)
                    })
            else:
                logger.info(f"  📥 No actionable big drops found on {target_date}")

        except Exception as e:
            logger.error(f"❌ Error processing data matrix for {target_date}: {e}")

    # Automatically overwrite your target JSON storage file
    output_file = "signals.json"
    with open(output_file, "w") as f:
        json.dump(all_extracted_signals, f, indent=4)
        
    logger.info(f"\n🎯 Execution complete. Generated {len(all_extracted_signals)} fresh weekday signals into '{output_file}'.")


if __name__ == "__main__":
    run_signal_pipeline()