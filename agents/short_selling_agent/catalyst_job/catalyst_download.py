import requests
import datetime
from typing import List, Dict, Any, Tuple

def download_biotech_catalysts(days_back: int = 2) -> List[Dict[str, Any]]:
    """
    Queries the ClinicalTrials.gov v2 API for interventional trials 
    modified within the specified window and extracts raw catalyst data.
    """
    url = "https://clinicaltrials.gov/api/v2/studies"
    
    # Calculate date range parameters
    today = datetime.date.today().strftime("%Y-%m-%d")
    start_date = (datetime.date.today() - datetime.timedelta(days=days_back)).strftime("%Y-%m-%d")
    
    print(f"⏳ [Download] Querying ClinicalTrials.gov for updates from {start_date} to {today}...")
    
    params = {
        "query.term": "AREA[StudyType]Interventional",
        "filter.advanced": f"AREA[LastUpdatePostDate]RANGE[{start_date}, {today}]",
        "pageSize": 100
    }
    
    parsed_records = []
    next_page_token = None
    
    while True:
        if next_page_token:
            params["nextPageToken"] = next_page_token
            
        response = requests.get(url, params=params)
        if response.status_code != 200:
            print(f"❌ [Download Error] API rejected request with status {response.status_code}: {response.text}")
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
            
            # Map structural field records
            parsed_records.append({
                "scraped_at": datetime.datetime.utcnow().isoformat(),
                "nct_id": nct_id,
                "sponsor": sponsor,
                "title": brief_title,
                "status": overall_status,
                "negative_reason": why_stopped
            })
            
        # Check if another pagination block exists
        next_page_token = payload.get("nextPageToken")
        if not next_page_token or not studies:
            break
            
    print(f"✨ [Download Complete] Extracted {len(parsed_records)} raw rows from API.")
    return parsed_records