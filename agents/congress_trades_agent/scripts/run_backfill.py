import datetime
import time
import sys
import os

# Ensure we can import the scraper from the same directory
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from scraper_contracts import fetch_and_store_contracts

# --- CONFIGURATION ---
# Backfill from Today back to Feb 1, 2024
START_DATE = datetime.date(2024, 2, 1)  
# We force the end date to avoid the "2026 system clock" issue
END_DATE   = datetime.date(2025, 2, 5) 
# ---------------------

def run_backfill():
    print(f"🚀 Starting Cloud Backfill Job")
    print(f"🎯 Target Range: {START_DATE} to {END_DATE}")
    
    # Start at the End Date and walk backwards
    current_cursor = END_DATE
    
    while current_cursor > START_DATE:
        # We process 5 days at a time (Safe for API timeouts)
        chunk_size = 5
        
        # Calculate window start
        window_start = current_cursor - datetime.timedelta(days=chunk_size)
        
        # Don't go past the start date
        if window_start < START_DATE:
            window_start = START_DATE
            
        # Format date string for the scraper function
        date_str = current_cursor.strftime("%Y-%m-%d")
        
        print(f"🔄 Processing Window Ending: {date_str} (Looking back {chunk_size} days)...")
        
        try:
            # Call the existing scraper logic
            fetch_and_store_contracts(days_back=chunk_size, end_date_str=date_str)
        except Exception as e:
            print(f"⚠️ Error in window {date_str}: {e}")
            # Continue to next window even if this one fails
        
        # Move cursor back
        current_cursor = window_start - datetime.timedelta(days=1)
        
        # Sleep to be polite to the API and avoid rate limits
        time.sleep(2)

    print("\n✅ Backfill Job Complete.")

if __name__ == "__main__":
    run_backfill()