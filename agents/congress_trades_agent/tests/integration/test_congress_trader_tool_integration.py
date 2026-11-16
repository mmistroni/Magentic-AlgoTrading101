import os
import uuid
from pathlib import Path
import pytest
from google.cloud import bigquery

from congress_trades_agent.schemas import (
    FundamentalEvaluation,
    TickerDecisionRecord
)
from congress_trades_agent.skills.congress_trader.tools import (
    get_fundamentals,
    fetch_historical_episodes,
    store_trade_decision
)

GCP_KEY_PATH = Path("gcp_key.json")
HAS_GCP_CREDS = GCP_KEY_PATH.exists() or bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))

TEST_TICKER = "NVDA"


def cleanup_test_decision(decision_id: str):
    """Helper to remove test records from BigQuery after test execution."""
    try:
        client = bigquery.Client()
        query = f"DELETE FROM `datamart.trade_decisions` WHERE decision_id = @decision_id"
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ScalarQueryParameter("decision_id", "STRING", decision_id)
            ]
        )
        client.query(query, job_config=job_config).result()
    except Exception as e:
        print(f"Warning: Failed to clean up test decision {decision_id}: {e}")


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_get_fundamentals_live():
    """Verify live fundamental data retrieval and Pydantic validation."""
    result = get_fundamentals(TEST_TICKER)
    assert isinstance(result, FundamentalEvaluation)
    assert result.ticker == TEST_TICKER
    assert isinstance(result.pe_ratio, float)
    assert result.valuation_verdict is not None
    assert 0.0 <= result.fundamental_health_score <= 100.0


@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS,
    reason="Integration test skipped: missing gcp_key.json or GOOGLE_APPLICATION_CREDENTIALS"
)
def test_store_and_fetch_trade_decision_full_fields_with_cleanup():
    """Verify storing trade decision populates all fields, round-trips correctly, and cleans up after itself."""
    
    # Optional: fetch live price first to use in our store call, or pass a mock/real float
    fund_data = get_fundamentals(TEST_TICKER)
    live_price = getattr(fund_data, "price", 138.50) or 138.50

    try:
        response_msg = store_trade_decision(
            ticker=TEST_TICKER,
            action="BUY",
            conviction_score=88.5,
            pe_ratio=31.2,
            valuation_verdict="UNDERVALUED",
            fundamental_health_score=85.0,
            congressional_net_buys=3,
            insider_cluster_buy=True,
            price=live_price,  # <-- Pass price here!
            synthesis_summary="Integration test checking full field population and cleanup."
        )
        assert "Successfully validated and stored decision record" in response_msg

        # Fetch episodes back from BigQuery to verify and capture the decision_id for cleanup
        episodes = fetch_historical_episodes(
            ticker=TEST_TICKER,
            min_conviction=80.0,
            limit=1
        )
        assert isinstance(episodes, list)
        assert len(episodes) > 0

        print("DEBUG EPISODES RETURNED:", episodes)  # <-- See what it actually contains

        latest_ep = episodes[0]
        test_decision_id = latest_ep["decision_id"]

        # Assert top-level fields (including entry_price if returned by your fetch executor)
        assert latest_ep["ticker"] == TEST_TICKER
        assert latest_ep["action"] == "BUY"
        assert latest_ep["conviction_score"] == 88.5
        assert latest_ep["decision_snapshot"] is not None

        # Assert nested JSON snapshot deserializes successfully back into TickerDecisionRecord
        snapshot_data = latest_ep["decision_snapshot"]
        if isinstance(snapshot_data, str):
            import json
            snapshot_data = json.loads(snapshot_data)

        record = TickerDecisionRecord(**snapshot_data)
        assert record.ticker == TEST_TICKER
        assert record.fundamentals.pe_ratio == 31.2
        assert record.signals_aggregated.congressional_net_buys == 3
        assert record.signals_aggregated.insider_cluster_buy is True
        assert "weights_applied" in snapshot_data

    finally:
        # Guarantee cleanup happens even if assertions fail
        if 'test_decision_id' in locals():
            cleanup_test_decision(test_decision_id)

@pytest.mark.integration
@pytest.mark.skipif(
    not HAS_GCP_CREDS or not os.environ.get("FMP_API_KEY"),
    reason="Integration test skipped: missing GCP credentials or FMP_API_KEY"
)
def test_store_fetch_and_calculate_trailing_return():
    """Verify that a stored trade decision can be fetched and evaluated for trailing return."""
    fund_data = get_fundamentals(TEST_TICKER)
    live_price = getattr(fund_data, "price", 138.50) or 138.50

    try:
        # 1. Store a decision with a known entry price
        response_msg = store_trade_decision(
            ticker=TEST_TICKER,
            action="BUY",
            conviction_score=85.0,
            pe_ratio=30.0,
            valuation_verdict="UNDERVALUED",
            fundamental_health_score=80.0,
            congressional_net_buys=2,
            insider_cluster_buy=True,
            price=live_price,
            synthesis_summary="Integration test for trailing return validation."
        )
        assert "Successfully validated and stored decision record" in response_msg

        # 2. Fetch the stored episode back
        episodes = fetch_historical_episodes(
            ticker=TEST_TICKER,
            min_conviction=80.0,
            limit=1
        )
        assert len(episodes) > 0
        latest_ep = episodes[0]
        test_decision_id = latest_ep.get("decision_id")
        
        # Safely grab timestamp supporting different key names and native datetimes
        raw_timestamp = latest_ep.get("decision_timestamp") or latest_ep.get("timestamp")
        assert raw_timestamp is not None, f"Could not find timestamp in episode record: {latest_ep}"
        
        if hasattr(raw_timestamp, "strftime"):
            entry_date = raw_timestamp.strftime("%Y-%m-%d")
        else:
            entry_date = str(raw_timestamp)[:10]  # Extract 'YYYY-MM-DD'
        
        stored_entry_price = latest_ep.get("entry_price", live_price)
        # 3. Call get_trailing_return using the fetched historical episode's date and entry price
        from congress_trades_agent.skills.congress_trader.tools import get_trailing_return
        
        return_result = get_trailing_return(
            ticker=TEST_TICKER,
            entry_date=entry_date,
            entry_price=stored_entry_price
        )

        # 4. Assert performance evaluation payload is valid
        assert isinstance(return_result, dict)
        assert "error" not in return_result, f"Trailing return error: {return_result.get('error')}"
        assert return_result["ticker"] == TEST_TICKER
        assert "trailing_return_pct" in return_result
        assert "current_price" in return_result

    finally:
        if 'test_decision_id' in locals() and test_decision_id:
            cleanup_test_decision(test_decision_id)