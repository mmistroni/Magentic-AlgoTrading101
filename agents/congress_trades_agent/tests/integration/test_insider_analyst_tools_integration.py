import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from google.adk.tools import ToolContext

from congress_trades_agent.schemas import (
    InsiderSignalsResponse,
    Form4DetailsResponse,
)
from congress_trades_agent.skills.insider_analyst.tools import (
    fetch_insider_signals,
    fetch_form4_details,
)

GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

TEST_DATE = "2026-09-14"


@pytest.fixture
def real_tool_context():
    """Initializes a live ToolContext instance for integration testing."""
    mock_invocation = MagicMock()
    mock_invocation.session.state = {
        "candidates": [],
        "confluence_reports": {},
    }
    context = ToolContext(invocation_context=mock_invocation)
    return context


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_fetch_insider_signals(real_tool_context):
    """Executes live fetch_insider_signals and asserts ToolContext state updates."""
    result = fetch_insider_signals(analysis_date=TEST_DATE, tool_context=real_tool_context)

    assert isinstance(result, InsiderSignalsResponse)
    assert result.error is None, f"Insider signals query failed: {result.error}"
    assert result.analysis_date == TEST_DATE
    assert isinstance(result.signals, list)
    assert result.count == len(result.signals)
    assert result.count > 0, f"Expected at least 1 signal for date {TEST_DATE}"

    first_signal = result.signals[0]
    assert hasattr(first_signal, "ticker")
    assert len(first_signal.ticker) > 0

    candidates = real_tool_context.state.get("candidates", [])
    assert len(candidates) > 0, "ToolContext state 'candidates' was not updated."
    
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
def test_fetch_form4_details(real_tool_context):
    """Executes live fetch_form4_details across a sequence and asserts ToolContext state updates."""
    insider_res = fetch_insider_signals(analysis_date=TEST_DATE, tool_context=real_tool_context)
    assert insider_res.error is None
    assert insider_res.count > 0, "Prerequisite failed: No Insider signals found"

    target_ticker = insider_res.signals[0].ticker

    form4_res = fetch_form4_details(
        ticker=target_ticker,
        analysis_date=TEST_DATE,
        tool_context=real_tool_context
    )

    assert isinstance(form4_res, Form4DetailsResponse)
    assert form4_res.error is None, f"Form 4 details query failed: {form4_res.error}"
    assert form4_res.ticker == target_ticker
    assert form4_res.analysis_date == TEST_DATE
    assert isinstance(form4_res.signals, list)
    assert form4_res.count == len(form4_res.signals)

    confluence_reports = real_tool_context.state.get("confluence_reports", {})
    assert target_ticker in confluence_reports, f"Target ticker {target_ticker} was not recorded in confluence_reports state."