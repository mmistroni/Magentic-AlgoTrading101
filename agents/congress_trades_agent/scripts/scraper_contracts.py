import os
import requests
import pandas as pd
import datetime
import time
import argparse
from google.cloud import bigquery
from io import BytesIO
import zipfile
from ticker_mapper import TickerMapper 

# CONFIG
PROJECT_ID = os.environ.get("PROJECT_ID", "datascience-projects")
DATASET_ID = "gcp_shareloader"
TABLE_ID = "contract_signals"

def fetch_and_store_contracts(days_back=3, end_date_str=None):
    """
    Fetches contracts for the past 'days_back' days.
    If end_date_str is provided, it calculates backwards from that date.
    """
    
    # 1. Determine Dates
    if end_date_str:
        try:
            target_date = datetime.datetime.strptime(end_date_str, "%Y-%m-%d").date()
        except ValueError:
            print("❌ Error: Invalid date format. Use YYYY-MM-DD.")
            return
    else:
        target_date = datetime.date.today()

    start_date_obj = target_date - datetime.timedelta(days=days_back)
    
    # API requires strings
    end_date_api = target_date.strftime("%Y-%m-%d")
    start_date_api = start_date_obj.strftime("%Y-%m-%d")

    print(f"🚀 Starting Scraper...")
    print(f"📅 Requesting window: {start_date_api} to {end_date_api} ({days_back} days)")

    # 2. Initialize Ticker Mapper
    try:
        print("📥 Initializing Ticker Mapper...")
        mapper = TickerMapper() 
        print("✅ Mapper loaded.")
    except Exception as e:
        print(f"❌ Mapper Critical Failure: {e}")
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
            # Wait longer for larger date ranges
            max_retries = 30 + (days_back * 2) 
            
            while retry_count < max_retries: 
                time.sleep(5) 
                try:
                    status_resp = requests.get(status_url).json()
                except:
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
            print("❌ Timed out.")
            return

        # Step C: Download with HTML Wait-Page Handling
        print(f"⬇️ Downloading CSV from {file_url}...")
        
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
                print(f"   ⚠️ Server 'Wait' page detected (Attempt {download_attempts+1}). Sleeping 10s...")
                time.sleep(10)
                download_attempts += 1
            
            # 3. Unknown Error
            else:
                print("❌ ERROR: Download returned unknown content.")
                print(f"   Preview: {csv_resp.text[:200]}")
                return

        if not csv_content:
            print("❌ Failed to retrieve ZIP file.")
            return

        # Step D: Process ZIP
        clean_rows = []
        try:
            with zipfile.ZipFile(BytesIO(csv_content)) as z:
                csv_filename = z.namelist()[0]
                print(f"📂 Processing file: {csv_filename}")
                
                with z.open(csv_filename) as f:
                    for chunk in pd.read_csv(f, chunksize=10000, low_memory=False):
                        
                        # Optimization: Filter by amount first
                        if 'total_obligation' in chunk.columns:
                            chunk = chunk[chunk['total_obligation'] > 500000]
                        
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
                                "amount": float(row.get('total_obligation', 0)),
                                "agency": row.get('awarding_agency_name', 'Unknown'),
                                "description": str(row.get('award_description', ''))[:1000]
                            })
                            
        except zipfile.BadZipFile:
            print("❌ ZIP Error: The file was corrupted.")
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
        print(f"✅ Upserted {len(rows)} rows to BigQuery.")
        client.delete_table(temp_table_id, not_found_ok=True)
        
    except Exception as e:
        print(f"❌ BigQuery Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--days", type=int, default=3, help="Days to look back")
    parser.add_argument("--end_date", type=str, default=None, help="YYYY-MM-DD (Optional override)")
    
    args = parser.parse_args()
    
    fetch_and_store_contracts(days_back=args.days, end_date_str=args.end_date)