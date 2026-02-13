import datetime
import time
import sys

# Import the scraper function from your existing file
try:
    from scraper_contracts import fetch_and_store_contracts
except ImportError:
    print("❌ Error: Could not find 'scraper_contracts.py' in this folder.")
    sys.exit(1)

# --- CONFIGURATION ---
# We want data from the start of 2024 up to the end of 2024 (or today)
START_DATE = datetime.date(2024, 1, 1)  
END_DATE   = datetime.date(2026, 1, 31) 
# ---------------------

def run_backfill():
    print(f"🕰️ Starting Historical Backfill: {START_DATE} -> {END_DATE}")
    print("------------------------------------------------------")
    
    # We start at the END and walk backwards to the START
    current_target = END_DATE
    
    while current_target >= START_DATE:
        # We process 5 days at a time to keep files small and fast
        days_window = 5 
        
        # Calculate the start of this mini-window
        window_start = current_target - datetime.timedelta(days=days_window)
        
        # Format date for the scraper
        # This overrides your system clock!
        date_str = current_target.strftime("%Y-%m-%d")
        
        print(f"\n🔄 Processing Window: {window_start} to {current_target}")
        
        # Call your existing scraper logic
        # We tell it: "Pretend today is 'date_str' and look back 5 days"
        fetch_and_store_contracts(days_back=days_window, end_date_str=date_str)
        
        # Move the cursor back for the next loop
        current_target = window_start - datetime.timedelta(days=1)
        
        # Sleep to prevent API throttling
        print("💤 Sleeping 3s...")
        time.sleep(3)

    print("\n✅ Backfill Complete for 2024.")

if __name__ == "__main__":
    run_backfill()