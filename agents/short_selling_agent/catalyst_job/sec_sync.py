import os
import re
import datetime
import httpx
from google.cloud import bigquery

SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_HEADERS = {"User-Agent": "MagenticAlgoAdmin admin@magenticalgotrading.co.uk"}

def fetch_and_clean_sec_tickers() -> list:
    """Fetches raw SEC data and normalizes company names into flat rows."""
    response = httpx.get(SEC_TICKER_URL, headers=SEC_HEADERS)
    response.raise_for_status()
    raw_data = response.json()
    
    cleaned_rows = []
    for item in raw_data.values():
        raw_title = item.get("title", "")
        ticker = item.get("ticker", "")
        cik = str(item.get("cik_str", ""))
        
        if not raw_title or not ticker:
            continue
            
        # Normalize name for bulletproof matching
        clean_name = raw_title.lower()
        clean_name = re.sub(r"[.,\-–]", "", clean_name)
        suffixes = r"\b(inc|corp|co|ltd|llc|plc|corporation|incorporated|limited)\b"
        clean_name = re.sub(suffixes, "", clean_name)
        clean_name = " ".join(clean_name.split()).strip()
        
        cleaned_rows.append({
            "cik": cik,
            "ticker": ticker,
            "company_name_raw": raw_title,
            "company_name_clean": clean_name,
            "sync_date": datetime.date.today().isoformat()
        })
    return cleaned_rows

def run_sec_sync(dataset_id: str = "gcp_shareloader", table_id: str = "sec_ticker_registry"):
    """Truncates and overwrites the BigQuery table with fresh master data weekly."""
    print("Fetching and cleaning master SEC data...")
    rows = fetch_and_clean_sec_tickers()
    
    bq_client = bigquery.Client()
    table_ref = bq_client.dataset(dataset_id).table(table_id)
    
    # Configure job to overwrite the table to keep it fresh and small
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE
    )
    
    print(f"Uploading {len(rows)} normalized SEC tickers to BigQuery...")
    job = bq_client.load_table_from_json(rows, table_ref, job_config=job_config)
    job.result()  # Wait for completion
    print("SEC Sync complete.")

if __name__ == "__main__":
    run_sec_sync()