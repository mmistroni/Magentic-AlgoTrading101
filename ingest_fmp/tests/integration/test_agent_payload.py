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
    tech_validator = TechnicalValidator(client=client, strict_mode=False, throttle_seconds=2)

    # Test candidate record
    candidate = {
        "symbol": "AAPL",
        "strategy_name": "agent_diagnostic_run",
        "timestamp": "2026-11-02T20:18:00Z"
    }

    print("\n" + "="*50)
    print("🚀 Running Strategic Stock Analyst Agent Payload Check on AAPL...")
    print("="*50)

    # 1. Run Fundamental Enrichment
    enriched = fund_validator.evaluate(candidate)
    if not enriched:
        print("❌ Fundamental validation failed.")
        return

    # 2. Run Technical & TA Indicator Enrichment
    enriched = tech_validator.evaluate(enriched)
    if not enriched:
        print("❌ Technical validation failed.")
        return

    # 3. Attach Beta & Profile Context (if not already attached)
    try:
        profile_url = f'https://financialmodelingprep.com/api/v3/profile/AAPL?apikey={api_key}'
        import requests
        profile_data = requests.get(profile_url).json()
        if profile_data:
            enriched['beta'] = profile_data[0].get('beta', 1.0)
    except Exception as e:
        enriched['beta'] = 1.0

    # 4. Define the exact fields required by the Strategic Stock Analyst Agent instructions
    required_agent_fields = [
        # Primary Trend
        "price", "sma20", "sma50", "sma200", "slope", "trend_velocity_gap",
        # Volume Confirmation
        "current_obv", "previous_obv", "obv_historical", "current_cmf", "previous_cmf",
        # Context & Volatility Filter
        "choppiness", "spx_choppiness", "beta",
        # Timing Momentum
        "RSI", "demarker"
    ]

    print("\n📦 Agent Enriched Payload Inspection:")
    for field in required_agent_fields:
        val = enriched.get(field)
        status = "✅" if val is not None else "⚠️ (Missing or None)"
        print(f"  {status} {field}: {val}")

    # Validate completeness
    missing = [f for f in required_agent_fields if enriched.get(f) is None]
    print("="*50)
    if missing:
        print(f"⚠️ Warning: The following agent-required fields are missing: {missing}")
    else:
        print("✨ SUCCESS: All fields required by the Strategic Stock Analyst Agent are present!")
    print("="*50)

if __name__ == "__main__":
    test_agent_enrichment_payload()