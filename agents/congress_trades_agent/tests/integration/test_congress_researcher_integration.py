import os
from pathlib import Path
import pytest

# Try importing from your module structure
try:
    from congress_trades_agent.skills.congress_researcher.tools import (
        fetch_congress_signals,
        fetch_contract_signals,
    )
except ModuleNotFoundError:
    from congress_trades_agent.skills.congress_researcher.tools import (
        fetch_congress_signals,
        fetch_contract_signals,
    )

from congress_trades_agent.schemas import (
    CongressSignalsResponse,
    ContractSignalsResponse,
)

# Resolve GCP credentials path relative to workspace root
GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

TEST_DATE = "2026-09-14"


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_fetch_congress_signals():
    """Executes live fetch_congress_signals function."""
    result = fetch_congress_signals(analysis_date=TEST_DATE)

    assert isinstance(result, CongressSignalsResponse)
    assert result.error is None, f"Congress signals query failed: {result.error}"
    assert result.analysis_date == TEST_DATE
    assert isinstance(result.signals, list)
    assert result.count == len(result.signals)
    assert result.count > 0, f"Expected at least 1 signal for date {TEST_DATE}"

    # Schema verification on first item
    first_signal = result.signals[0]
    assert hasattr(first_signal, "ticker")
    assert len(first_signal.ticker) > 0


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_fetch_contract_signals():
    """Executes live fetch_contract_signals function for a ticker returned by congress signals."""
    # Step 1: Dynamic ticker lookup
    congress_res = fetch_congress_signals(analysis_date=TEST_DATE)
    assert congress_res.error is None
    assert congress_res.count > 0, "Prerequisite failed: No Congress signals found"

    target_ticker = congress_res.signals[0].ticker

    # Step 2: Query contract signals
    contract_res = fetch_contract_signals(
        ticker=target_ticker,
        analysis_date=TEST_DATE
    )

    assert isinstance(contract_res, ContractSignalsResponse)
    assert contract_res.error is None, f"Contract signals query failed: {contract_res.error}"
    assert contract_res.ticker == target_ticker
    assert contract_res.analysis_date == TEST_DATE
    assert isinstance(contract_res.signals, list)
    assert contract_res.count == len(contract_res.signals)
    assert hasattr(contract_res, "total_contract_spend_usd")