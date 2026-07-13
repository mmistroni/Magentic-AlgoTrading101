import os
import requests
import datetime
import argparse
from typing import List, Dict, Any
from google.cloud import bigquery

# --- Configuration Mapping ---
PROJECT_ID = os.environ.get("PROJECT_ID", "datascience-projects")
DATASET_ID = "gcp_shareloader"
TABLE_ID = "biotech_catalysts"

def log(msg: str):
    """Helper formatting logger for consistent execution timestamps."""
    print(f"[{datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] {msg}", flush=True)

def validate_date(date_string: str) -> str:
    """Validates that the CLI input matches YYYY-MM-DD format."""
    try:
        datetime.datetime.strptime(date_string, "%Y-%m-%d")
        return date_string
    except ValueError:
        raise argparse.ArgumentTypeError(
            f"Invalid date format: '{date_string}'. Must be in YYYY-MM-DD format."
        )

def download_historical_catalysts(start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Queries the ClinicalTrials.gov v2 API for interventional trials 
    modified within an explicit historical range window.
    """
    url = "https://clinicaltrials.gov/api/v2/studies"
    
    log(f"⏳ [Download] Scanning historical updates from {start_date} to {end_date}...")
    ## We use the exact RANGE syntax matching your daily framework configuration
    
    params = {
        # Combine the phase, study type, and industry sponsor type all into the main query term
        "query.term": "AREA[StudyType]Interventional AND (AREA[Phase]Phase 2 OR AREA[Phase]Phase 3) AND AREA[LeadSponsorClass]INDUSTRY",
        
        # Keep the advanced filter strictly for your historical date range
        "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{start_date}, {end_date}]",
        
        "pageSize": 100
    }
    
    parsed_records = []
    next_page_token = None
    page_count = 0
    
    while True:
        page_count += 1
        if next_page_token:
            # CHANGE THIS LINE: Key must be "pageToken", value is next_page_token
            params["pageToken"] = next_page_token
        else:
            params.pop("pageToken", None)    
                
        log(f"   🔄 Fetching page {page_count}...")
        response = requests.get(url, params=params)
        if response.status_code != 200:
            log(f"❌ [Download Error] API Request Rejected ({response.status_code}): {response.text}")
            break
            
        payload = response.json()
        studies = payload.get("studies", [])
        
        for study in studies:
            protocol = study.get("protocolSection", {})
            id_info = protocol.get("identificationModule", {})
            status_info = protocol.get("statusModule", {})
            sponsor_info = protocol.get("sponsorCollaboratorsModule", {})
            
            nct_id = id_info.get("nctId")
            brief_title = id_info.get("briefTitle")
            overall_status = status_info.get("overallStatus")
            why_stopped = status_info.get("whyStopped", None)
            sponsor = sponsor_info.get("leadSponsor", {}).get("name")
            
            parsed_records.append({
                "scraped_at": datetime.datetime.utcnow().isoformat(),
                "nct_id": nct_id,
                "sponsor": sponsor,
                "title": brief_title,
                "status": overall_status,
                "negative_reason": why_stopped
            })
            
        next_page_token = payload.get("nextPageToken")
        if not next_page_token or not studies:
            break
            
    log(f"✅ [Download Complete] Extracted {len(parsed_records)} raw records over {page_count} pages.")
    return parsed_records

def store_catalysts_in_bigquery(records: List[Dict[str, Any]]):
    """
    Appends the parsed rows directly to the daily-partitioned BigQuery table.
    """
    if not records:
        log("⚠️ [Storage] No new records found to append. Skipping BigQuery ingestion.")
        return
        
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
    
    schema = [
        bigquery.SchemaField("scraped_at", "TIMESTAMP", mode="REQUIRED"),
        bigquery.SchemaField("nct_id", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("sponsor", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("title", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("status", "STRING", mode="NULLABLE"),
        bigquery.SchemaField("negative_reason", "STRING", mode="NULLABLE"),
    ]
    
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_APPEND"
    )
    
    log(f"📦 [Storage] Committing {len(records)} data payloads to BigQuery table: {table_ref}...")
    try:
        job = client.load_table_from_json(records, table_ref, job_config=job_config)
        job.result()  
        log("✨ [Storage Complete] Database write transaction succeeded.")
    except Exception as e:
        log(f"❌ [Storage Error] Failed to write data to BigQuery: {e}")

def run_historical_pipeline(start_date: str, end_date: str):
    """Orchestrates the historical data extraction pipeline flow sequentially."""
    log(f"🚀 Starting Historical Biotech Catalyst Backfill Pipeline [{start_date} to {end_date}]...")
    
    # Step 1: Extract
    extracted_data = download_historical_catalysts(start_date=start_date, end_date=end_date)
    
    # Step 2: Load
    store_catalysts_in_bigquery(extracted_data)
    
    log("🏁 Historical batch pipeline execution finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Biotech Catalyst Historical Backfill Engine")
    parser.add_argument(
        "--start-date", 
        type=validate_date,
        required=True, 
        help="The start execution date in YYYY-MM-DD format"
    )
    parser.add_argument(
        "--end-date", 
        type=validate_date,
        required=True, 
        help="The end execution date in YYYY-MM-DD format"
    )
    
    args = parser.parse_args()
    run_historical_pipeline(start_date=args.start_date, end_date=args.end_date)