import datetime
import time
import sys
import os

# --- PATH SETUP ---
# This ensures we can import 'scraper_contracts' from the same folder
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from scraper_contracts import fetch_and_store_contracts

def get_date_from_env(var_name, default_date):
    val = os.environ.get(var_name)
    if not val:
        return default_date
    try:
        return datetime.datetime.strptime(val, "%Y-%m-%d").date()
    except ValueError:
        print(f"❌ Error: Invalid format for {var_name} ({val}). Use YYYY-MM-DD.")
        sys.exit(1)

# --- CONFIGURATION ---
# 1. Try to get dates from Cloud Run Environment Variables
# 2. If not set, default to a safe recent window (e.g., Feb 2025)
default_start = datetime.date(2025, 2, 1)
default_end   = datetime.date(2025, 4, 14)

START_DATE = get_date_from_env("BACKFILL_START", default_start)
END_DATE   = get_date_from_env("BACKFILL_END", default_end)
# ---------------------

def run_backfill():
    print(f"🚀 Starting Cloud Backfill Job")
    print(f"⚙️ Configuration: START={START_DATE} | END={END_DATE}")
    
    if START_DATE >= END_DATE:
        print("❌ Error: Start Date must be before End Date.")
        return

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
            # Call the scraper function
            fetch_and_store_contracts(days_back=chunk_size, end_date_str=date_str)
        except Exception as e:
            print(f"⚠️ Error in window {date_str}: {e}")
        
        # Move cursor back
        current_cursor = window_start - datetime.timedelta(days=1)
        
        # Sleep to be polite to the API
        time.sleep(3)

    print("\n✅ Backfill Job Complete.")

if __name__ == "__main__":
    run_backfill()