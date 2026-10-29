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