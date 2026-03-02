import cloudscraper
import time
import os
from google.cloud import bigquery
import json

# --- CONFIG ---
PROJECT_ID = os.environ.get("PROJECT_ID", "datascience-projects")
DATASET_ID = "gcp_shareloader"
STAGING_TABLE_ID = "senate_disclosures_staging"

# Capitol Trades API (Hidden Backend)
API_URL = "https://bff.capitoltrades.com/trades"

def fetch_and_stage_senate_data():
    print("🕵️  Fetching 2024 Senate Trades (Cloudflare Bypass)...")
    
    # Create a CloudScraper Instance (Bypasses 503/403)
    scraper = cloudscraper.create_scraper()
    
    all_trades = []
    page = 1
    
    while True:
        # Params: Senate, 2024, 100 items per page
        params = {
            "page": page,
            "pageSize": 100,
            "chamber": "senate",
            "year": 2024
        }
        
        try:
            print(f"   Requesting Page {page}...", end="\r")
            
            # Use scraper.get instead of requests.get
            r = scraper.get(API_URL, params=params)
            
            if r.status_code != 200:
                print(f"\n❌ Error: API returned {r.status_code}")
                # If 403/503 persists, we stop.
                break
            
            data = r.json().get('data', [])
            
            if not data:
                print("\n✅ Reached end of data.")
                break
            
            for t in data:
                # 1. Extract & Clean Ticker
                issuer = t.get('issuer', {})
                ticker = issuer.get('ticker')
                
                # Filter garbage tickers
                if not ticker or ':' in ticker or len(ticker) > 5: 
                    continue
                
                # 2. Extract Politician
                politician = t.get('politician', {})
                name = f"{politician.get('firstName')} {politician.get('lastName')}".strip()

                # 3. Extract Details
                tx_date = t.get('txDate')
                tx_type = t.get('txType')
                amount = t.get('size', {}).get('label', 'Unknown')

                all_trades.append({
                    "AS_OF_DATE": tx_date,
                    "DISCLOSURE": tx_type.title() if tx_type else "Unknown",
                    "TICKER": ticker,
                    "representative": name,
                    "amount": amount
                })
            
            page += 1
            # Sleep slightly to not trigger aggressive rate limits
            time.sleep(2)
            
        except Exception as e:
            print(f"\n❌ Script Error: {e}")
            break

    print(f"\n\n💎 TOTAL Valid 2024 Trades Collected: {len(all_trades)}")
    
    if all_trades:
        upload_to_staging(all_trades)
    else:
        print("⚠️ No data found. The API might have hardened even against cloudscraper.")
        print("💡 Plan B: Use 2025 data for Proof of Concept.")

def upload_to_staging(rows):
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{STAGING_TABLE_ID}"
    
    schema = [
        bigquery.SchemaField("AS_OF_DATE", "DATE"),
        bigquery.SchemaField("DISCLOSURE", "STRING"),
        bigquery.SchemaField("TICKER", "STRING"),
        bigquery.SchemaField("representative", "STRING"),
        bigquery.SchemaField("amount", "STRING")
    ]
    
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE",
    )

    print(f"📤 Uploading {len(rows)} rows to STAGING...")
    job = client.load_table_from_json(rows, table_ref, job_config=job_config)
    job.result()
    print("✅ Staging Upload Complete. Now run the SQL Merge.")

if __name__ == "__main__":
    fetch_and_stage_senate_data()