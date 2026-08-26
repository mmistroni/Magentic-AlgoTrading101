import os
from pathlib import Path
import pytest

from congress_trades_agent.skills.congress_researcher.tools import fetch_congress_signals
from congress_trades_agent.schemas import CongressSignalsResponse

# Resolve GCP credentials path relative to workspace root
GCP_KEY_PATH = Path("/workspaces/Magentic-AlgoTrading101/gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_bigquery_live_connection_and_query():
    """Executes live query against BigQuery to verify connection, credentials, and SQL execution."""
    # Test date targeting known historical dataset
    test_date = "2026-08-14"
    
    # 1. Direct call to tool function
    result = fetch_congress_signals(analysis_date=test_date)

    # 2. Connection and execution checks
    assert isinstance(result, CongressSignalsResponse)
    assert result.error is None, f"BigQuery connection/query failed with error: {result.error}"
    assert result.analysis_date == test_date
    assert isinstance(result.signals, list)
    assert result.count == len(result.signals)
    assert result.count > 0, "Expected at least one signal in the response"