import os
import datetime
import asyncio
from typing import Optional, List, Dict, Any
import httpx
from pydantic import BaseModel, Field, field_validator
from google.cloud import bigquery

# SEC Endpoint for mapping CIK/Tickers to Company Names
SEC_TICKER_URL = "https://www.sec.gov/files/company_tickers.json"
SEC_HEADERS = {"User-Agent": "MagenticAlgoAdmin admin@magenticalgotrading.co.uk"}

# =====================================================================
# 1. DATA LAYERING & MODELS
# =====================================================================
class ClinicalCatalyst(BaseModel):
    nct_id: str
    ticker: str
    sponsor_name: str
    primary_completion_date: Optional[datetime.date] = None
    phase: str
    condition_targeted: str
    last_updated: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    @field_validator("primary_completion_date", mode="before")
    @classmethod
    def parse_completion_date(cls, value: Any) -> Optional[datetime.date]:
        """Safely parses ClinicalTrials.gov fuzzy dates (e.g. '2026-06') to a valid DATE object."""
        if not value or value == "Unknown":
            return None
        if isinstance(value, str) and len(value) == 7:  # Format: YYYY-MM
            try:
                return datetime.datetime.strptime(value, "%Y-%m").date()
            except ValueError:
                return None
        return value

# =====================================================================
# 2. CLINICAL TRIALS API V2 CLIENT
# =====================================================================
class ClinicalTrialsClient:
    BASE_URL = "https://clinicaltrials.gov/api/v2/studies"

    def __init__(self, ticker_map: Dict[str, str]):
        """Accepts a structured map of normalized { 'lowercase sponsor name': 'TICKER' }"""
        self.ticker_map = ticker_map

    def _match_ticker(self, sponsor_name: str) -> Optional[str]:
        """Anti-hallucination guard to resolve trial sponsor directly to a public ticker."""
        if not sponsor_name:
            return None
        clean_sponsor = sponsor_name.lower().replace(".", "").replace(",", "").strip()
        
        # 1. Attempt exact lookup match
        if clean_sponsor in self.ticker_map:
            return self.ticker_map[clean_sponsor]
            
        # 2. Fallback to partial substring scan to capture 'Inc' / 'Ltd' variants
        for sec_name, symbol in self.ticker_map.items():
            if clean_sponsor in sec_name or sec_name in clean_sponsor:
                return symbol
        return None

    async def fetch_phase3_catalysts(self, limit: int = 50) -> List[ClinicalCatalyst]:
        """Queries the official ClinicalTrials.gov v2 API for high-impact milestones."""
        params = {
            "filter.phase": "PHASE3",
            "filter.overallStatus": "ACTIVE_NOT_RECRUITING",  # Trials currently wrapping up data
            "pageSize": str(limit)
        }
        
        async with httpx.AsyncClient() as client:
            response = await client.get(self.BASE_URL, params=params)
            response.raise_for_status()
            payload = response.json()
            
        catalysts = []
        for study in payload.get("studies", []):
            protocol = study.get("protocolSection", {})
            id_module = protocol.get("identificationModule", {})
            status_module = protocol.get("statusModule", {})
            sponsor_module = protocol.get("sponsorCollaboratorsModule", {})
            
            sponsor_name = sponsor_module.get("leadSponsor", {}).get("name", "")
            ticker = self._match_ticker(sponsor_name)
            
            # Drop unmapped private entities or generic non-profits immediately
            if ticker:
                comp_date_str = status_module.get("primaryCompletionDateStruct", {}).get("date")
                conditions = protocol.get("conditionsModule", {}).get("conditions", [])
                
                catalysts.append(
                    ClinicalCatalyst(
                        nct_id=id_module.get("nctId"),
                        ticker=ticker,
                        sponsor_name=sponsor_name,
                        primary_completion_date=comp_date_str,
                        phase="PHASE3",
                        condition_targeted=", ".join(conditions)
                    )
                )
        return catalysts

# =====================================================================
# 3. BIGQUERY JOB ORCHESTRATION
# =====================================================================
def fetch_sec_ticker_registry() -> Dict[str, str]:
    """Retrieves the official master index from the SEC EDGAR system."""
    response = httpx.get(SEC_TICKER_URL, headers=SEC_HEADERS)
    response.raise_for_status()
    data = response.json()
    
    ticker_map = {}
    for item in data.values():
        clean_name = item['title'].lower().replace('.', '').replace(',', '').strip()
        ticker_map[clean_name] = item['ticker']
    return ticker_map

async def main(dataset_id: str = "biotech_trading", table_id: str = "catalyst_watch_list"):
    """Main execution block designed to run as an autonomous Cloud Run Job."""
    print("Initializing BigQuery engine connection...")
    bq_client = bigquery.Client()
    table_ref = bq_client.dataset(dataset_id).table(table_id)
    
    # Run pipeline stages
    ticker_registry = fetch_sec_ticker_registry()
    api_client = ClinicalTrialsClient(ticker_map=ticker_registry)
    
    print("Fetching active Phase 3 trials from registry...")
    catalysts = await api_client.fetch_phase3_catalysts()
    
    if not catalysts:
        print("Pipeline cycle complete: No new public ticker milestones identified.")
        return
        
    # Serialize data into native BigQuery streaming configurations
    rows_to_insert = []
    for item in catalysts:
        row = item.model_dump()
        if row["primary_completion_date"]:
            row["primary_completion_date"] = row["primary_completion_date"].isoformat()
        row["last_updated"] = row["last_updated"].isoformat()
        rows_to_insert.append(row)
        
    print(f"Streaming {len(rows_to_insert)} structured records directly to BigQuery...")
    errors = bq_client.insert_rows_json(table_ref, rows_to_insert)
    if errors:
        raise RuntimeError(f"BigQuery streaming data extraction failed: {errors}")
    
    print(f"Success! Catalyst data synchronization complete for target: {dataset_id}.{table_id}")

if __name__ == "__main__":
    asyncio.run(main())