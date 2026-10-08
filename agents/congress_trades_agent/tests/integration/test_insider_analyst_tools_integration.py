import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest
from google.adk.tools import ToolContext

from congress_trades_agent.schemas import (
    Form4SignalsResponse,
    LobbyingSignalsResponse,
)
from congress_trades_agent.skills.insider_analyst.tools import (
    fetch_form4_signals,
    fetch_lobbying_signals,
)

# Resolve GCP credentials path relative to workspace root
GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

TEST_DATE = "2026-09-14"
TEST_INSIDER_TICKER = "JEF"      # Verified insider buy ticker from BigQuery
TEST_LOBBYING_TICKER = "WYNN"    # Verified lobbying spend ticker from BigQuery


@pytest.fixture
def real_tool_context():
    """Initializes a live ToolContext instance for integration testing."""
    mock_invocation = MagicMock()
    mock_invocation.session.state = {
        "confluence_reports": {},
    }
    context = ToolContext(invocation_context=mock_invocation)
    # Ensure tool_context.state direct property access resolves smoothly in ADK
    if not hasattr(context, "_state") or context._state is None:
        context.state = mock_invocation.session.state
    return context


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_fetch_form4_signals_insider_only(real_tool_context):
    """Scenario 1: Insider signals direct tool call check for ticker JEF."""
    result = fetch_form4_signals(
        ticker=TEST_INSIDER_TICKER,
        analysis_date=TEST_DATE,
        tool_context=real_tool_context,
    )

    assert isinstance(result, Form4SignalsResponse)
    assert result.error is None, f"Form 4 query failed: {result.error}"
    assert isinstance(result.signals, list)
    assert result.count == len(result.signals)
    assert result.count > 0, f"Expected at least 1 Form 4 signal for ticker {TEST_INSIDER_TICKER}"

    # Verify signal schema fields
    first_signal = result.signals[0]
    assert hasattr(first_signal, "ticker")
    assert first_signal.ticker == TEST_INSIDER_TICKER

    # ToolContext state assertion: tools mutate confluence_reports[ticker]
    confluence_reports = real_tool_context.state.get("confluence_reports", {})
    assert TEST_INSIDER_TICKER in confluence_reports, (
        f"ToolContext state 'confluence_reports' was not updated for {TEST_INSIDER_TICKER}."
    )
    assert "form4_signal" in confluence_reports[TEST_INSIDER_TICKER]


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_fetch_lobbying_signals_lobbying_only(real_tool_context):
    """Scenario 2: Lobbying signals direct tool call check for ticker WYNN."""
    result = fetch_lobbying_signals(
        ticker=TEST_LOBBYING_TICKER,
        analysis_date=TEST_DATE,
        tool_context=real_tool_context,
    )

    assert isinstance(result, LobbyingSignalsResponse)
    assert result.error is None, f"Lobbying signals query failed: {result.error}"
    assert isinstance(result.signals, list)
    assert result.count == len(result.signals)
    assert result.count > 0, f"Expected at least 1 lobbying signal for ticker {TEST_LOBBYING_TICKER}"

    # Verify signal schema fields
    first_signal = result.signals[0]
    assert hasattr(first_signal, "ticker")
    assert first_signal.ticker == TEST_LOBBYING_TICKER

    # ToolContext state assertion
    confluence_reports = real_tool_context.state.get("confluence_reports", {})
    assert TEST_LOBBYING_TICKER in confluence_reports, (
        f"ToolContext state 'confluence_reports' was not updated for {TEST_LOBBYING_TICKER}."
    )
    assert "lobbying_spend_usd" in confluence_reports[TEST_LOBBYING_TICKER]


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_fetch_combined_signals(real_tool_context):
    """Scenario 3: Sequential combination of Form 4 and Lobbying signals updating tool context."""
    # Step 1: Query Form 4 insider signals
    form4_res = fetch_form4_signals(
        ticker=TEST_INSIDER_TICKER,
        analysis_date=TEST_DATE,
        tool_context=real_tool_context,
    )
    assert isinstance(form4_res, Form4SignalsResponse)
    assert form4_res.error is None

    # Step 2: Query Lobbying signals for the same ticker
    lobbying_res = fetch_lobbying_signals(
        ticker=TEST_INSIDER_TICKER,
        analysis_date=TEST_DATE,
        tool_context=real_tool_context,
    )
    assert isinstance(lobbying_res, LobbyingSignalsResponse)
    assert lobbying_res.error is None

    # ToolContext state assertions for confluence tracking
    confluence_reports = real_tool_context.state.get("confluence_reports", {})
    assert TEST_INSIDER_TICKER in confluence_reports, (
        f"Ticker {TEST_INSIDER_TICKER} was not recorded in confluence_reports state."
    )
    report = confluence_reports[TEST_INSIDER_TICKER]
    assert "form4_signal" in report
    assert "lobbying_spend_usd" in report