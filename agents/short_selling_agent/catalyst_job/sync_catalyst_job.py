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

def download_biotech_catalysts(days_back: int) -> List[Dict[str, Any]]:
    """
    Queries the ClinicalTrials.gov v2 API for interventional trials 
    modified within the calculation window and parses key catalyst signals.
    """
    url = "https://clinicaltrials.gov/api/v2/studies"
    
    # Establish precise date parameters
    today_str = datetime.date.today().strftime("%Y-%m-%d")
    start_date_str = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    log(f"⏳ [Download] Scanning updates from {start_date_str} to {today_str}...")
    
    params = {
        "query.term": "AREA[StudyType]Interventional",
        "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{start_date_str}, {today_str}]",
        "pageSize": 100
    }
    
    parsed_records = []
    next_page_token = None
    
    while True:
        if next_page_token:
            params["nextPageToken"] = next_page_token
            
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
            
    log(f"✅ [Download Complete] Extracted {len(parsed_records)} raw records.")
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
    
    # Enforce safe explicit structure matching your SQL configuration schema
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
        job.result()  # Block main execution until the transaction completes successfully
        log("✨ [Storage Complete] Database write transaction succeeded.")
    except Exception as e:
        log(f"❌ [Storage Error] Failed to write data to BigQuery: {e}")

def run_sync_pipeline(days_back: int):
    """Orchestrates the data extraction pipeline flow sequentially."""
    log("🚀 Starting Daily Biotech Catalyst Sync Job Pipeline...")
    
    # Step 1: Execute Extract Layer
    extracted_data = download_biotech_catalysts(days_back=days_back)
    
    # Step 2: Execute Load Layer
    store_catalysts_in_bigquery(extracted_data)
    
    log("🏁 Pipeline execution finished.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Biotech Catalyst Data Synchronization Engine")
    parser.add_argument(
        "--days", 
        type=int, 
        default=2, 
        help="Number of historical lookup tracking days back to pull updates for (Default: 2)"
    )
    
    args = parser.parse_args()
    run_sync_pipeline(days_back=args.days)