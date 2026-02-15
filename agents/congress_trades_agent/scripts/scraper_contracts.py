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
    
    # 1. Determine Dates
    if not end_date_str:
        end_date_str = os.environ.get("OVERRIDE_DATE")
    
    if end_date_str:
        try:
            target_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            target_date = datetime.date.today()
    else:
        target_date = datetime.date.today()

    start_date_obj = target_date - datetime.timedelta(days=days_back)
    end_date_api = target_date.strftime("%Y-%m-%d")
    start_date_api = start_date_obj.strftime("%Y-%m-%d")

    log(f"📅 RUNNING: {start_date_api} to {end_date_api}")

    # 2. Initialize Ticker Mapper
    try:
        log("📥 Initializing Ticker Mapper...")
        mapper = TickerMapper() 
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
        init_resp = response.json()
        file_url = init_resp.get('file_url')
        status_url = init_resp.get('status_url')

        # Step B: POLLING (Wait for file to be ready)
        log(f"🔄 Waiting for file generation...")
        ready = False
        for i in range(20): # Try for 100 seconds
            time.sleep(5) 
            status_resp = requests.get(status_url).json()
            status = status_resp.get('status')
            if status == 'finished':
                file_url = status_resp.get('file_url') # Ensure we have the final URL
                ready = True
                break
            elif status == 'failed':
                log(f"❌ API Failed: {status_resp.get('message')}")
                return
            log(f"   ...status: {status}")
        
        if not ready:
            log("❌ Timed out waiting for API generation.")
            return

        # Step C: Robust Download Loop
        log(f"⬇️ Downloading CSV from {file_url}...")
        csv_content = None
        
        for attempt in range(10):
            try:
                r = requests.get(file_url)
                # Check Magic Bytes (PK = Zip)
                if r.content.startswith(b'PK'):
                    csv_content = r.content
                    log("✅ Download Successful (ZIP found).")
                    break
                else:
                    log(f"   ⚠️ Attempt {attempt+1}: File not ready (Server returned text/html). Retrying in 5s...")
                    time.sleep(5)
            except Exception as e:
                log(f"   ⚠️ Network error: {e}")
                time.sleep(5)

        if not csv_content:
            log("❌ Critical Error: Could not download valid ZIP file after multiple attempts.")
            return

        # Step D: Process ZIP
        clean_rows = []
        with zipfile.ZipFile(BytesIO(csv_content)) as z:
            csv_filename = z.namelist()[0]
            log(f"📂 Processing: {csv_filename}")
            
            with z.open(csv_filename) as f:
                # Read Headers first to find the column name
                header = pd.read_csv(f, nrows=1)
                cols = list(header.columns)
                
                # Determine Amount Column
                amount_col = 'federal_action_obligation' if 'federal_action_obligation' in cols else None
                if not amount_col and 'total_dollars_obligated' in cols: amount_col = 'total_dollars_obligated'
                
                if not amount_col:
                    log(f"❌ Columns Found: {cols}")
                    log("❌ ERROR: Could not find obligation amount column.")
                    return

                # Reset file pointer
                f.seek(0)
                
                for chunk in pd.read_csv(f, chunksize=5000, low_memory=False):
                    
                    # Convert column to numeric
                    chunk[amount_col] = pd.to_numeric(chunk[amount_col], errors='coerce').fillna(0)
                    
                    # Filter > \$500k
                    chunk = chunk[chunk[amount_col] > 500000]
                    if chunk.empty: continue

                    for _, row in chunk.iterrows():
                        recipient = str(row.get('recipient_name', '')).upper()
                        
                        if not any(x in recipient for x in [' INC', ' CORP', ' PLC', ' LTD', ' CO']):
                            continue

                        ticker = mapper.find_ticker(recipient)
                        if not ticker: continue
                        
                        clean_rows.append({
                            "action_date": row.get('action_date'),
                            "recipient_name": recipient,
                            "ticker": ticker,
                            "amount": float(row.get(amount_col, 0)),
                            "agency": row.get('awarding_agency_name', 'Unknown'),
                            "description": str(row.get('award_description', ''))[:1000]
                        })

        log(f"✨ Found {len(clean_rows)} relevant corporate contracts.")

        # 5. Load to BigQuery
        if clean_rows:
            upsert_to_bigquery(clean_rows)
        else:
            log("⚠️ No rows found (filtered out).")

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
    parser.add_argument("--days", type=int, default=2)
    parser.add_argument("--end_date", type=str, default=None)
    
    args = parser.parse_args()
    fetch_and_store_contracts(days_back=args.days, end_date_str=args.end_date)