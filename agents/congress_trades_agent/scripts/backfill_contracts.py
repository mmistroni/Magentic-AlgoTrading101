import datetime
import time
import sys
import os

# --- PATH SETUP ---
# This ensures we can import 'scraper_contracts' from the same folder
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

# Now we can import the function from your scraper file
from scraper_contracts import fetch_and_store_contracts

# --- CONFIGURATION ---
# Backfill from Today back to Feb 1, 2024
START_DATE = datetime.date(2024, 2, 1)  
END_DATE   = datetime.date(2025, 2, 14) 

# ---------------------

def run_backfill():
    print(f"🚀 Starting Cloud Backfill Job")
    print(f"🎯 Target Range: {START_DATE} to {END_DATE}")
    
    # Start at the End Date and walk backwards
    current_cursor = END_DATE
    
    while current_cursor > START_DATE:
        # We use 7 days because your scraper logic prefers 7 days
        chunk_size = 7
        
        # Calculate window start
        window_start = current_cursor - datetime.timedelta(days=chunk_size)
        
        # Don't go past the start date
        if window_start < START_DATE:
            window_start = START_DATE
            
        # Format date string for the scraper function
        date_str = current_cursor.strftime("%Y-%m-%d")
        
        print(f"🔄 Processing Window Ending: {date_str} (Looking back {chunk_size} days)...")
        
        try:
            # Call the scraper function you already wrote
            # It will handle the API calls and BigQuery upload
            fetch_and_store_contracts(days_back=chunk_size, end_date_str=date_str)
        except Exception as e:
            print(f"⚠️ Error in window {date_str}: {e}")
        
        # Move cursor back (Overlap by 1 day to be safe, or just move back by chunk)
        current_cursor = window_start - datetime.timedelta(days=1)
        
        # Sleep to be polite to the API
        time.sleep(3)

    print("\n✅ Backfill Job Complete.")

if __name__ == "__main__":
    run_backfill()