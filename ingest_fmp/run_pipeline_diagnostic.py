import os
import logging
from ingest_fmp.client import FMPClient
from ingest_fmp.fundamental_validator import FundamentalValidator
from ingest_fmp.technical_validator import TechnicalValidator

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_agent_enrichment_payload():
    api_key = os.environ.get("FMP_API_KEY")
    if not api_key:
        print("❌ FMP_API_KEY environment variable not set.")
        return

    client = FMPClient(api_key=api_key)
    
    # Initialize validators with relaxed bounds to ensure AAPL passes for inspection
    fund_validator = FundamentalValidator(
        client=client,
        min_eps_growth=-999.0,
        min_roe=-999.0,
        min_gross_margin=-999.0,
        max_institutional_ownership=1.0
    )
    tech_validator = TechnicalValidator(client=client, strict_mode=False, throttle_seconds=5)

    # Test candidate record
    candidate = {
        "symbol": "AAPL",
        "strategy_name": "agent_diagnostic_run",
        "timestamp": "2026-11-02T20:18:00Z"
    }

    print("\n" + "="*50)
    print("🚀 Running Agent Enrichment Diagnostic on AAPL...")
    print("="*50)

    # 1. Run Fundamental Enrichment
    enriched = fund_validator.evaluate(candidate)
    if not enriched:
        print("❌ Fundamental validation failed.")
        return

    # 2. Run Technical Enrichment
    enriched = tech_validator.evaluate(enriched)
    if not enriched:
        print("❌ Technical validation failed.")
        return

    # 3. Fetch Quote / 52W High Context
    quote_data = client.get_quote("AAPL")
    if quote_data:
        q = quote_data[0]
        enriched.update({
            "current_price": q.get("price"),
            "year_high": q.get("yearHigh"),
            "year_low": q.get("yearLow"),
            "relative_volume": q.get("relVolume")
        })

    print("\n📦 Final Enriched Payload for Agent / BigQuery:")
    for key, value in enriched.items():
        print(f"  - {key}: {value}")
    print("="*50)

if __name__ == "__main__":
    test_agent_enrichment_payload()