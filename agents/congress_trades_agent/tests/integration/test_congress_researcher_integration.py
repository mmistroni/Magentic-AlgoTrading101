import os
from pathlib import Path
import pytest
from google.adk.tools import ToolContext

from congress_trades_agent.schemas import (
    CongressSignalsResponse,
    ContractSignalsResponse,
)
from congress_trades_agent.skills.congress_researcher.tools import (
    fetch_congress_signals,
    fetch_contract_signals,
)

# Resolve GCP credentials path relative to workspace root
GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

TEST_DATE = "2026-09-14"


@pytest.fixture
def real_tool_context():
    """Initializes a live ToolContext instance for integration testing."""
    context = ToolContext()
    context.state = {
        "candidates": [],
        "confluence_reports": {},
    }
    return context


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_fetch_congress_signals(real_tool_context):
    """Executes live fetch_congress_signals and asserts ToolContext state updates."""
    result = fetch_congress_signals(analysis_date=TEST_DATE, tool_context=real_tool_context)

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

    # ToolContext state assertions
    candidates = real_tool_context.state.get("candidates", [])
    assert len(candidates) > 0, "ToolContext state 'candidates' was not updated."
    
    # Handle list of dicts or list of Pydantic models in state
    candidate_tickers = [
        c.ticker if hasattr(c, "ticker") else c.get("ticker")
        for c in candidates
    ]
    assert first_signal.ticker in candidate_tickers


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_fetch_contract_signals(real_tool_context):
    """Executes live fetch_contract_signals across a sequence and asserts ToolContext state updates."""
    # Step 1: Dynamic ticker lookup & update context
    congress_res = fetch_congress_signals(analysis_date=TEST_DATE, tool_context=real_tool_context)
    assert congress_res.error is None
    assert congress_res.count > 0, "Prerequisite failed: No Congress signals found"

    target_ticker = congress_res.signals[0].ticker

    # Step 2: Query contract signals & update context
    contract_res = fetch_contract_signals(
        ticker=target_ticker,
        analysis_date=TEST_DATE,
        tool_context=real_tool_context
    )

    assert isinstance(contract_res, ContractSignalsResponse)
    assert contract_res.error is None, f"Contract signals query failed: {contract_res.error}"
    assert contract_res.ticker == target_ticker
    assert contract_res.analysis_date == TEST_DATE
    assert isinstance(contract_res.signals, list)
    assert contract_res.count == len(contract_res.signals)
    assert hasattr(contract_res, "total_contract_spend_usd")

    # ToolContext state assertions for confluence reports
    confluence_reports = real_tool_context.state.get("confluence_reports", {})
    assert target_ticker in confluence_reports, f"Target ticker {target_ticker} was not recorded in confluence_reports state."