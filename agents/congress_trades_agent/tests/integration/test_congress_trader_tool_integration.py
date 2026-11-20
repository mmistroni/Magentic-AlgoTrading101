import os
import json
from datetime import datetime, timedelta, timezone
from pathlib import Path
from types import SimpleNamespace
import pytest
from google.cloud import bigquery

from congress_trades_agent.schemas import (
    FundamentalEvaluation,
    TickerDecisionRecord,
)
from congress_trades_agent.skills.congress_trader.tools import (
    get_confluence_report,
    get_fundamentals,
    fetch_historical_episodes,
    store_trade_decision,
    get_trailing_return,
)

GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

TEST_TICKER = "NVDA"


def cleanup_test_decision(decision_id: str):
    """Helper to remove test records from BigQuery after test execution."""
    try:
        client = bigquery.Client()
        query = "DELETE FROM `datamart.trade_decisions` WHERE decision_id = @decision_id"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("decision_id", "STRING", decision_id)
            ]
        )
        client.query(query, job_config=job_config).result()
    except Exception as e:
        print(f"Warning: Failed to clean up test decision {decision_id}: {e}")


def test_get_confluence_report_state_handoff_empty_and_populated():
    """Verify get_confluence_report cleanly handles empty and populated state payloads."""
    empty_ctx = SimpleNamespace(state={"confluence_reports": {}, "candidates": []})
    empty_res = get_confluence_report(tool_context=empty_ctx)
    assert empty_res["has_signals"] is False
    assert empty_res["tickers"] == []
    assert empty_res["status"] == "EMPTY_CONFLUENCE"

    populated_ctx = SimpleNamespace(
        state={
            "candidates": [{"ticker": "GS", "net_buy_activity": 200000.0}],
            "confluence_reports": {
                "GS": {
                    "gov_contracts_spend_usd": 10_000_000.0,
                    "form4_signal": "Cluster Buy",
                    "lobbying_spend_usd": 300_000.0,
                }
            },
        }
    )
    pop_res = get_confluence_report(tool_context=populated_ctx)
    assert pop_res["has_signals"] is True
    assert pop_res["status"] == "OK"
    assert pop_res["tickers"] == ["GS"]


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS or not os.environ.get("FMP_API_KEY"),
    reason="Integration test skipped: missing GCP credentials or FMP_API_KEY",
)
def test_get_fundamentals_live():
    """Verify live fundamental data retrieval and Pydantic model compatibility."""
    result = get_fundamentals(TEST_TICKER)
    assert isinstance(result, dict)
    parsed = FundamentalEvaluation(**result)
    assert parsed.ticker == TEST_TICKER
    assert isinstance(parsed.pe_ratio, float)
    assert parsed.valuation_verdict is not None
    assert 0.0 <= parsed.fundamental_health_score <= 100.0


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS or not os.environ.get("FMP_API_KEY"),
    reason="Integration test skipped: missing GCP credentials or FMP_API_KEY",
)
def test_store_and_fetch_trade_decision_full_fields_with_cleanup():
    """Verify storing trade decision populates all fields, round-trips correctly, and cleans up."""
    fund_data = get_fundamentals(TEST_TICKER)
    assert isinstance(fund_data, dict)
    live_price = fund_data.get("price")
    assert live_price is not None and float(live_price) > 0, (
        f"Expected valid live price for {TEST_TICKER}, got {live_price}"
    )

    test_decision_id: str | None = None
    marker_summary = f"Integ full-field check {os.urandom(4).hex()}"

    try:
        response_msg = store_trade_decision(
            ticker=TEST_TICKER,
            action="BUY",
            conviction_score=88.5,
            pe_ratio=float(fund_data.get("pe_ratio") or 31.2),
            valuation_verdict="UNDERVALUED",
            fundamental_health_score=85.0,
            congressional_net_buys=3,
            insider_cluster_buy=True,
            price=float(live_price),
            synthesis_summary=marker_summary,
        )
        assert "Successfully validated and stored decision record" in response_msg

        episodes = fetch_historical_episodes(
            ticker=TEST_TICKER,
            min_conviction=80.0,
            limit=10,
        )
        assert isinstance(episodes, list) and len(episodes) > 0

        matched = None
        for ep in episodes:
            snap = ep.get("decision_snapshot")
            snap_dict = json.loads(snap) if isinstance(snap, str) else (snap or {})
            summary = (
                snap_dict.get("rationale", {}) or {}
            ).get("final_synthesis_summary", "")
            if marker_summary in summary:
                matched = (ep, snap_dict)
                break

        assert matched is not None, "Could not locate newly inserted test episode in fetched rows"
        latest_ep, snapshot_data = matched
        test_decision_id = latest_ep["decision_id"]

        assert latest_ep["ticker"] == TEST_TICKER
        assert latest_ep["action"] == "BUY"
        assert latest_ep["conviction_score"] == 88.5

        record = TickerDecisionRecord(**snapshot_data)
        assert record.ticker == TEST_TICKER
        assert record.signals_aggregated.congressional_net_buys == 3
        assert record.signals_aggregated.insider_cluster_buy is True
        assert "weights_applied" in snapshot_data
    finally:
        if test_decision_id:
            cleanup_test_decision(test_decision_id)


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS or not os.environ.get("FMP_API_KEY"),
    reason="Integration test skipped: missing GCP credentials or FMP_API_KEY",
)
def test_store_fetch_and_calculate_trailing_return():
    """Verify that a stored trade decision can be fetched and evaluated for trailing return."""
    fund_data = get_fundamentals(TEST_TICKER)
    assert isinstance(fund_data, dict)
    live_price = fund_data.get("price")
    assert live_price is not None and float(live_price) > 0, (
        f"Expected valid live price for {TEST_TICKER}, got {live_price}"
    )

    test_decision_id: str | None = None
    marker_summary = f"Integ trailing return check {os.urandom(4).hex()}"

    try:
        response_msg = store_trade_decision(
            ticker=TEST_TICKER,
            action="BUY",
            conviction_score=85.0,
            pe_ratio=float(fund_data.get("pe_ratio") or 30.0),
            valuation_verdict="UNDERVALUED",
            fundamental_health_score=80.0,
            congressional_net_buys=2,
            insider_cluster_buy=True,
            price=float(live_price),
            synthesis_summary=marker_summary,
        )
        assert "Successfully validated and stored decision record" in response_msg

        episodes = fetch_historical_episodes(
            ticker=TEST_TICKER,
            min_conviction=80.0,
            limit=10,
        )
        matched = None
        for ep in episodes:
            snap = ep.get("decision_snapshot")
            snap_dict = json.loads(snap) if isinstance(snap, str) else (snap or {})
            summary = (
                snap_dict.get("rationale", {}) or {}
            ).get("final_synthesis_summary", "")
            if marker_summary in summary:
                matched = ep
                break

        assert matched is not None, "Could not locate newly inserted trailing-return episode"
        test_decision_id = matched.get("decision_id")
        stored_entry_price = matched.get("entry_price", float(live_price))

        past_entry_date = (datetime.now(timezone.utc) - timedelta(days=30)).strftime("%Y-%m-%d")
        return_result = get_trailing_return(
            ticker=TEST_TICKER,
            entry_date=past_entry_date,
            entry_price=stored_entry_price,
        )

        assert isinstance(return_result, dict)
        assert "error" not in return_result, f"Trailing return error: {return_result.get('error')}"
        assert return_result["ticker"] == TEST_TICKER
        assert "trailing_return_pct" in return_result
        assert "current_price" in return_result
    finally:
        if test_decision_id:
            cleanup_test_decision(test_decision_id)