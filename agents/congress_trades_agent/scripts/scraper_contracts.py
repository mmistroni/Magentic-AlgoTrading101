import os
import requests
import pandas as pd
import datetime
import time
import argparse
import json
from google.cloud import bigquery
from io import BytesIO
import zipfile
from ticker_mapper import TickerMapper 

# CONFIG
PROJECT_ID = os.environ.get("PROJECT_ID", "datascience-projects")
DATASET_ID = "gcp_shareloader"
TABLE_ID = "contract_signals"

def log(msg):
    print(f"[{datetime.datetime.now()}] {msg}", flush=True)

def fetch_and_store_contracts(days_back=2, end_date_str=None):
    """
    Scrapes USAspending.gov for the past 'days_back' days.
    Default is 2 days.
    """
    log(f"🚀 Starting Government Contract Scraper (Window: {days_back} days)...")
    
    # 1. Determine Dates
    # Priority: 1. Function Arg -> 2. Env Var -> 3. System Clock
    if not end_date_str:
        end_date_str = os.environ.get("OVERRIDE_DATE")

    if end_date_str:
        try:
            target_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
            log(f"⚠️ Using OVERRIDE date: {target_date}")
        except ValueError:
            log("❌ Error: Invalid date format in override. Using System Clock.")
            target_date = datetime.date.today()
    else:
        target_date = datetime.date.today()

    # Safety Check for 2026+ System Clocks
    if target_date.year > 2025:
        log(f"⚠️ WARNING: System clock is set to {target_date.year}. This looks incorrect.")
        log("   If the API returns no data, set the 'OVERRIDE_DATE' environment variable in Cloud Run.")

    # Calculate Window
    start_date_obj = target_date - datetime.timedelta(days=days_back)
    end_date_api = target_date.strftime("%Y-%m-%d")
    start_date_api = start_date_obj.strftime("%Y-%m-%d")

    log(f"📅 Requesting Data: {start_date_api} to {end_date_api}")

    # 2. Initialize Ticker Mapper
    try:
        log("📥 Initializing Ticker Mapper...")
        mapper = TickerMapper() 
        log("✅ Mapper loaded.")
    except Exception as e:
        log(f"❌ Mapper Critical Failure: {e}")
        return

    # 3. USASpending API Payload
    url = "https://api.usaspending.gov/api/v2/bulk_download/awards/"
    payload = {
        "filters": {
            "prime_award_types": ["A", "B", "C", "D"], 
            "date_type": "action_date",
            "date_range": {
                "start_date": start_date_api,
                "end_date": end_date_api
            }
        },
        "file_format": "csv"
    }
    
    try:
        # Step A: Initiate Download
        log("⏳ Contacting USASpending API...")
        response = requests.post(url, json=payload)
        
        if response.status_code != 200:
            log(f"❌ API Error {response.status_code}: {response.text}")
            return

        init_resp = response.json()
        file_url = init_resp.get('file_url')
        status_url = init_resp.get('status_url')

        log(f"ℹ️ Tracking URL: {status_url}")

        # Step B: POLLING
        if not file_url and status_url:
            log(f"🔄 Waiting for file generation...")
            retry_count = 0
            max_retries = 40 # Wait up to 3-4 minutes
            
            while retry_count < max_retries: 
                time.sleep(5) 
                try:
                    status_resp = requests.get(status_url).json()
                except:
                    continue

                status = status_resp.get('status')
                if retry_count % 5 == 0:
                    log(f"   ...status: {status}")

                if status == 'finished':
                    file_url = status_resp.get('file_url')
                    log("✅ File ready.")
                    break
                elif status == 'failed':
                    log(f"❌ Generation Failed: {status_resp.get('message')}")
                    return
                
                retry_count += 1
        
        if not file_url:
            log("❌ Timed out waiting for file generation.")
            return

        # Step C: Download with Retry Logic
        log(f"⬇️ Downloading CSV...")
        
        csv_content = None
        download_attempts = 0
        
        while download_attempts < 10:
            csv_resp = requests.get(file_url)
            
            # 1. Success (ZIP Header)
            if csv_resp.content.startswith(b'PK'):
                csv_content = csv_resp.content
                break 
            
            # 2. Waiting Room (HTML)
            elif b'<html' in csv_resp.content.lower():
                log(f"   ⚠️ Server preparing download (Attempt {download_attempts+1}). Sleeping 10s...")
                time.sleep(10)
                download_attempts += 1
            
            # 3. Error
            else:
                log(f"❌ ERROR: unexpected content type.")
                log(f"   Preview: {csv_resp.text[:200]}")
                return

        if not csv_content:
            log("❌ Failed to retrieve ZIP file.")
            return

        # Step D: Process ZIP
        clean_rows = []
        try:
            with zipfile.ZipFile(BytesIO(csv_content)) as z:
                csv_filename = z.namelist()[0]
                log(f"📂 Processing: {csv_filename}")
                
                with z.open(csv_filename) as f:
                    for chunk in pd.read_csv(f, chunksize=10000, low_memory=False):
                        
                        # Optimization: Filter by amount first
                        if 'total_obligation' in chunk.columns:
                            chunk = chunk[chunk['total_obligation'] > 500000]
                        
                        if chunk.empty: continue

                        for _, row in chunk.iterrows():
                            recipient = str(row.get('recipient_name', '')).upper()
                            
                            # Basic string filter
                            if not any(x in recipient for x in [' INC', ' CORP', ' PLC', ' LTD', ' CO']):
                                continue

                            ticker = mapper.find_ticker(recipient)
                            if not ticker: continue
                            
                            clean_rows.append({
                                "action_date": row.get('action_date'),
                                "recipient_name": recipient,
                                "ticker": ticker,
                                "amount": float(row.get('total_obligation', 0)),
                                "agency": row.get('awarding_agency_name', 'Unknown'),
                                "description": str(row.get('award_description', ''))[:1000]
                            })
                            
        except zipfile.BadZipFile:
            log("❌ ZIP Error: The file was corrupted.")
            return

        log(f"✨ Found {len(clean_rows)} relevant corporate contracts.")

        # 5. Load to BigQuery
        if clean_rows:
            upsert_to_bigquery(clean_rows)
        else:
            log("⚠️ Download successful, but no relevant contracts found.")

    except Exception as e:
        log(f"❌ Script Crashed: {e}")

def upsert_to_bigquery(rows):
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
        temp_table_id = f"{PROJECT_ID}.{DATASET_ID}.temp_contracts_{int(time.time())}"
        
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
        log(f"✅ Upserted {len(rows)} rows to BigQuery.")
        client.delete_table(temp_table_id, not_found_ok=True)
        
    except Exception as e:
        log(f"❌ BigQuery Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    # CHANGED DEFAULT TO 2
    parser.add_argument("--days", type=int, default=2, help="Days to look back")
    parser.add_argument("--end_date", type=str, default=None, help="YYYY-MM-DD")
    
    args = parser.parse_args()
    
    fetch_and_store_contracts(days_back=args.days, end_date_str=args.end_date)