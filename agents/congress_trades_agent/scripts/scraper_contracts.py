import os
import requests
import pandas as pd
import datetime
from google.cloud import bigquery
from io import BytesIO
import zipfile
from .ticker_mapper import TickerMapper

# CONFIG
PROJECT_ID = os.environ.get("PROJECT_ID", "datascience-projects")
DATASET_ID = "gcp_shareloader"
TABLE_ID = "contract_signals"

def fetch_and_store_contracts():
    print("🚀 Starting Government Contract Scraper...")
    
    mapper = TickerMapper()

    # 1. Calculate Date Range (Yesterday's Data)
    # USASpending updates daily. We grab the last 24 hours of signed contracts.
    today = datetime.date.today()
    yesterday = today - datetime.timedelta(days=1)
    date_str = yesterday.strftime("%Y-%m-%d")
    
    print(f"📅 Fetching contracts signed on: {date_str}")

    # 2. Call USASpending Bulk API
    # We use the 'prime_awards' endpoint which gives us the raw CSV
    url = "https://api.usaspending.gov/api/v2/bulk_download/awards/"
    payload = {
        "filters": {
            "prime_award_types": ["A", "B", "C", "D"], # Contracts only
            "date_type": "action_date",
            "date_range": {
                "start_date": date_str,
                "end_date": date_str
            },
            "agencies": [{"tier": "toptier", "name": "All"}] 
        },
        "file_format": "csv"
    }
    
    try:
        # Step A: Request the Download
        print("⏳ Requesting download generation...")
        init_resp = requests.post(url, json=payload).json()
        file_url = init_resp.get('file_url')
        
        if not file_url:
            print("❌ No file generated. API might be busy or no data.")
            return

        # Step B: Download the CSV (It might be large, so stream it)
        print(f"⬇️ Downloading: {file_url}")
        csv_resp = requests.get(file_url)
        
        # Step C: Unzip and Parse
        with zipfile.ZipFile(BytesIO(csv_resp.content)) as z:
            # There is usually one CSV inside
            csv_filename = z.namelist()[0]
            with z.open(csv_filename) as f:
                df = pd.read_csv(f, low_memory=False)

        print(f"✅ Downloaded {len(df)} raw records.")

        # 3. Transform & Clean
        # We only care about: Who got it, How much, Who gave it
        clean_rows = []
        
        for _, row in df.iterrows():
            amount = row.get('total_obligation', 0)
            recipient = str(row.get('recipient_name', '')).upper()

            ticker = mapper.find_ticker(recipient)
        
            # If no ticker found, it's likely a private company -> Skip
            if not ticker:
                continue

            
            # Filter 1: Must be a significant amount (> \$500k)
            if amount < 500000: continue
            
            # Filter 2: Must look like a public company (Inc, Corp, PLC)
            # This reduces noise from small private LLCs/individuals
            if not any(x in recipient for x in [' INC', ' CORP', ' PLC', ' LTD', ' CO']):
                continue

            clean_rows.append({
                "action_date": date_str,
                "recipient_name": recipient,
                "ticker": ticker, # Helper to map names
                "amount": float(amount),
                "agency": row.get('awarding_agency_name', 'Unknown'),
                "description": str(row.get('award_description', ''))[:500]
            })

        print(f"✨ Filtered down to {len(clean_rows)} high-value corporate contracts.")

        # 4. Load to BigQuery
        if clean_rows:
            client = bigquery.Client()
            table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
            
            # Insert
            errors = client.insert_rows_json(table_ref, clean_rows)
            if errors:
                print(f"❌ BQ Insert Error: {errors}")
            else:
                print(f"✅ Success! Loaded {len(clean_rows)} contracts to BigQuery.")
        else:
            print("⚠️ No relevant contracts found today.")

    except Exception as e:
        print(f"❌ Scraper Failed: {e}")

# Helper: Simple Ticker Mapping (Optional but useful)
# In production, you'd load a master mapping table from BQ
def _guess_ticker(name):
    # Dictionary of top 50 contractors
    mapping = {
        "LOCKHEED MARTIN": "LMT",
        "BOEING": "BA",
        "RAYTHEON": "RTX",
        "GENERAL DYNAMICS": "GD",
        "NORTHROP GRUMMAN": "NOC",
        "PFIZER": "PFE",
        "MODERNA": "MRNA",
        "MICROSOFT": "MSFT",
        "AMAZON": "AMZN",
        "GOOGLE": "GOOGL"
    }
    for key, val in mapping.items():
        if key in name:
            return val
    return None # Unknown

if __name__ == "__main__":
    fetch_and_store_contracts()