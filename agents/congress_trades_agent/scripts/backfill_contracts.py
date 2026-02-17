import datetime
import time
import sys
import os
import argparse  # <--- Added to handle Console Arguments

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from scraper_contracts import fetch_and_store_contracts

def parse_date(date_str):
    try:
        return datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
    except ValueError:
        print(f"❌ Error: Invalid date format '{date_str}'. Use YYYY-MM-DD.")
        sys.exit(1)

def run_backfill(start_date, end_date):
    print(f"🚀 Starting Cloud Backfill Job")
    print(f"⚙️ Configuration: START={start_date} | END={end_date}")
    
    if start_date >= end_date:
        print("❌ Error: Start Date must be before End Date.")
        return

    # Start at the End Date and walk backwards
    current_cursor = end_date
    
    while current_cursor > start_date:
        # We use 7 days because your scraper logic prefers 7 days
        chunk_size = 7
        
        # Calculate window start
        window_start = current_cursor - datetime.timedelta(days=chunk_size)
        
        # Don't go past the start date
        if window_start < start_date:
            window_start = start_date
            
        # Format date string for the scraper function
        date_str = current_cursor.strftime("%Y-%m-%d")
        
        print(f"🔄 Processing Window Ending: {date_str} (Looking back {chunk_size} days)...")
        
        try:
            # Call the scraper function
            fetch_and_store_contracts(days_back=chunk_size, end_date_str=date_str)
        except Exception as e:
            print(f"⚠️ Error in window {date_str}: {e}")
        
        # Move cursor back (Ensure no overlap, jump to the day before the window)
        current_cursor = window_start - datetime.timedelta(days=1)
        
        # Sleep to be polite to the API
        time.sleep(3)

    print("\n✅ Backfill Job Complete.")

if __name__ == "__main__":
    # 1. Setup Argument Parser
    parser = argparse.ArgumentParser()
    parser.add_argument("--start", help="Start Date (YYYY-MM-DD)")
    parser.add_argument("--end", help="End Date (YYYY-MM-DD)")
    
    args = parser.parse_args()

    # 2. Define Defaults (Feb 2024 to Feb 2025 as a safe baseline)
    default_start = datetime.date(2024, 2, 1)
    default_end = datetime.date(2025, 2, 14)

    # 3. Priority: Command Line Args -> Environment Vars -> Defaults
    if args.start:
        final_start = parse_date(args.start)
    elif os.environ.get("BACKFILL_START"):
        final_start = parse_date(os.environ.get("BACKFILL_START"))
    else:
        final_start = default_start

    if args.end:
        final_end = parse_date(args.end)
    elif os.environ.get("BACKFILL_END"):
        final_end = parse_date(os.environ.get("BACKFILL_END"))
    else:
        final_end = default_end

    # 4. Run
    run_backfill(final_start, final_end)