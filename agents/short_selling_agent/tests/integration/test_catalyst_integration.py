import asyncio
import sys
from catalyst_job.catalyst_job import load_ticker_map_from_bq, ClinicalTrialsClient

async def inspect_live_catalysts(limit: int = 20):
    print("============================================================")
    print("🔬 STARTING LIVE CATALYST INSPECTION")
    print("============================================================")
    
    # 1. Fetch your verified master registry from BigQuery
    try:
        print("📥 Loading cached ticker maps from BigQuery registry...")
        ticker_map = load_ticker_map_from_bq()
        print(f"✅ Successfully loaded {len(ticker_map)} company-to-ticker maps.")
    except Exception as e:
        print(f"❌ Error reading from BigQuery: {e}")
        print("Ensure your local gcloud authentication details are active.")
        sys.exit(1)
        
    print("\n📡 Querying ClinicalTrials.gov v2 API for active Phase 3 milestones...")
    
    # 2. Instantiate our verified anti-hallucination client
    client = ClinicalTrialsClient(ticker_map=ticker_map)
    
    # 3. Pull records through the verification filter
    catalysts = await client.fetch_phase3_catalysts(limit=limit)
    
    print(f"🎯 Filter Complete: Found {len(catalysts)} active public market catalysts out of top {limit} entries.\n")
    print(f"{'TICKER':<8} | {'TRIAL ID':<12} | {'EST. READOUT':<12} | {'SPONSOR & CONDITION'}")
    print("-" * 90)
    
    for item in catalysts:
        date_str = item.primary_completion_date.strftime("%Y-%m-%d") if item.primary_completion_date else "Unknown"
        print(f"{item.ticker:<8} | {item.nct_id:<12} | {date_str:<12} | {item.sponsor_name}")
        print(f"{'':<39} ↳ Target: {item.condition_targeted[:50]}")
        print("-" * 90)

if __name__ == "__main__":
    # Allow passing custom limits via terminal command arguments
    max_records = int(sys.argv[1]) if len(sys.argv) > 1 else 20
    asyncio.run(inspect_live_catalysts(limit=max_records))