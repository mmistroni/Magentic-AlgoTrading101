import os
import requests
import pandas as pd
import datetime
import time
from google.cloud import bigquery
from io import BytesIO
import zipfile
from ticker_mapper import TickerMapper 

# CONFIG
PROJECT_ID = os.environ.get("PROJECT_ID", "datascience-projects")
DATASET_ID = "gcp_shareloader"
TABLE_ID = "contract_signals"

def fetch_and_store_contracts():
    print("🚀 Starting Government Contract Scraper (Robust Mode)...")
    
    # 1. Initialize Ticker Mapper
    try:
        print("📥 Initializing Ticker Mapper...")
        mapper = TickerMapper() 
        print("✅ Mapper loaded successfully.")
    except Exception as e:
        print(f"❌ Mapper Critical Failure: {e}")
        return

    # 2. Calculate Date Range
    # NOTE: Your logs showed 2026. If your system clock is wrong, this will fail.
    today = datetime.date.today()
    if today.year > 2025:
        print(f"⚠️ WARNING: System clock is set to {today.year}. API calls may fail if data doesn't exist yet.")
        
    end_date_str = today.strftime("%Y-%m-%d")
    start_date_str = (today - datetime.timedelta(days=3)).strftime("%Y-%m-%d")
    
    print(f"📅 Requesting contracts for window: {start_date_str} to {end_date_str}")

    # 3. USASpending API Payload
    url = "https://api.usaspending.gov/api/v2/bulk_download/awards/"
    payload = {
        "filters": {
            "prime_award_types": ["A", "B", "C", "D"], 
            "date_type": "action_date",
            "date_range": {
                "start_date": start_date_str,
                "end_date": end_date_str
            }
        },
        "file_format": "csv"
    }
    
    try:
        # Step A: Initiate Download
        print("⏳ Contacting USASpending API...")
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            print(f"❌ API Error {response.status_code}: {response.text}")
            return

        init_resp = response.json()
        file_url = init_resp.get('file_url')
        status_url = init_resp.get('status_url')

        print(f"ℹ️ Status URL: {status_url}")

        # Step B: POLLING
        if not file_url and status_url:
            print(f"🔄 Polling for file generation...")
            retry_count = 0
            while retry_count < 20: # Wait up to 100s
                time.sleep(5) 
                try:
                    status_resp = requests.get(status_url).json()
                except:
                    print("   ...network glitch, retrying...")
                    continue

                status = status_resp.get('status')
                print(f"   ...attempt {retry_count+1}: {status}")

                if status == 'finished':
                    file_url = status_resp.get('file_url')
                    print("✅ File generated.")
                    break
                elif status == 'failed':
                    print(f"❌ Generation Failed: {status_resp.get('message')}")
                    return
                
                retry_count += 1
        
        if not file_url:
            print("❌ Timed out. The API is busy or the date range has no data.")
            return

        # Step C: Download & Parse (With Safety Checks)
        print(f"⬇️ Downloading CSV from {file_url}...")
        csv_resp = requests.get(file_url)
        
        # --- NEW SAFETY CHECK ---
        # If the file doesn't start with 'PK' (Magic bytes for Zip), it's likely an error message.
        if not csv_resp.content.startswith(b'PK'):
            print("❌ ERROR: Downloaded file is not a valid ZIP.")
            print(f"   Server Response Content: {csv_resp.text[:500]}") # Print first 500 chars of error
            return
        # ------------------------

        clean_rows = []
        try:
            with zipfile.ZipFile(BytesIO(csv_resp.content)) as z:
                # API sometimes returns multiple files, usually we want the first CSV
                csv_filename = z.namelist()[0]
                print(f"📂 Processing file: {csv_filename}")
                
                with z.open(csv_filename) as f:
                    # Use chunking for large files
                    for chunk in pd.read_csv(f, chunksize=10000, low_memory=False):
                        
                        # Filter for High Value (> \$500k) FIRST for speed
                        # Ensure column exists before filtering
                        if 'total_obligation' in chunk.columns:
                            chunk = chunk[chunk['total_obligation'] > 500000]
                        
                        if chunk.empty: continue

                        for _, row in chunk.iterrows():
                            recipient = str(row.get('recipient_name', '')).upper()
                            
                            # Heuristic Filter: Must look like a public company
                            if not any(x in recipient for x in [' INC', ' CORP', ' PLC', ' LTD', ' CO']):
                                continue

                            # Map Ticker
                            ticker = mapper.find_ticker(recipient)
                            if not ticker: continue
                            
                            # Prepare Row
                            clean_rows.append({
                                "action_date": row.get('action_date'),
                                "recipient_name": recipient,
                                "ticker": ticker,
                                "amount": float(row.get('total_obligation', 0)),
                                "agency": row.get('awarding_agency_name', 'Unknown'),
                                "description": str(row.get('award_description', ''))[:1000]
                            })
                            
        except zipfile.BadZipFile:
            print("❌ ZIP Error: The file was corrupted or incomplete.")
            return

        print(f"✨ Found {len(clean_rows)} relevant corporate contracts.")

        # 5. Load to BigQuery
        if clean_rows:
            upsert_to_bigquery(clean_rows)
        else:
            print("⚠️ Download successful, but no public company contracts found > \$500k.")

    except Exception as e:
        print(f"❌ Script Crashed: {e}")

def upsert_to_bigquery(rows):
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
        
        # 1. Temp Table
        temp_table_id = f"{PROJECT_ID}.{DATASET_ID}.temp_contracts_{int(time.time())}"
        
        # Define Schema explicitly to avoid type errors
        schema = [
            bigquery.SchemaField("action_date", "DATE"),
            bigquery.SchemaField("recipient_name", "STRING"),
            bigquery.SchemaField("ticker", "STRING"),
            bigquery.SchemaField("amount", "FLOAT"),
            bigquery.SchemaField("agency", "STRING"),
            bigquery.SchemaField("description", "STRING"),
        ]
        
        job_config = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")
        job = client.load_table_from_json(rows, temp_table_id, job_config=job_config)
        job.result()
        
        # 2. Merge (Deduplicate)
        # We identify duplicates by: Ticker, Date, Amount, and Agency
        query = f"""
        MERGE `{table_id}` T
        USING `{temp_table_id}` S
        ON T.ticker = S.ticker 
           AND T.action_date = S.action_date 
           AND T.amount = S.amount
           AND T.agency = S.agency
        WHEN NOT MATCHED THEN
          INSERT (action_date, recipient_name, ticker, amount, agency, description)
          VALUES (action_date, recipient_name, ticker, amount, agency, description)
        """
        
        client.query(query).result()
        print(f"✅ Upserted {len(rows)} rows to BigQuery.")
        
        client.delete_table(temp_table_id, not_found_ok=True)
        
    except Exception as e:
        print(f"❌ BigQuery Error: {e}")

if __name__ == "__main__":
    fetch_and_store_contracts()