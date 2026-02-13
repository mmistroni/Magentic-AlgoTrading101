import datetime
import time
from scraper_contracts import fetch_and_store_contracts

# CONFIG: How far back to go?
START_DATE = datetime.date(2023, 1, 1) # Start of 2023
END_DATE = datetime.date(2024, 11, 20) # Up to today (adjust as needed)

def run_backfill():
    print(f"🕰️ Starting Historical Backfill from {START_DATE} to {END_DATE}...")
    
    current_end = END_DATE
    
    # We step backwards in 7-day chunks to be safe with API limits
    while current_end > START_DATE:
        # Calculate the start of this 7-day chunk
        current_start = current_end - datetime.timedelta(days=6)
        
        # Override date string format for the scraper
        date_str = current_end.strftime("%Y-%m-%d")
        
        print(f"\n--- Processing Window: {current_start} to {current_end} ---")
        
        # Call your existing function (forcing the end date)
        # We use days_back=6 to cover the 7-day window (End date counts as day 0)
        fetch_and_store_contracts(days_back=6, end_date_str=date_str)
        
        # Move the window back
        current_end = current_start - datetime.timedelta(days=1)
        
        # Sleep to be nice to the API
        time.sleep(5)

if __name__ == "__main__":
    run_backfill()