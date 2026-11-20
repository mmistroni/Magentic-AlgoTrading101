from types import SimpleNamespace
from unittest.mock import patch, MagicMock
import pytest

from congress_trades_agent.skills.congress_trader.tools import (
    get_confluence_report,
    get_fundamentals,
    store_trade_decision,
    fetch_historical_episodes,
    get_trailing_return,
)
from congress_trades_agent.schemas import FundamentalEvaluation


def _make_tool_context(state: dict | None):
    if state is None:
        return SimpleNamespace(state=None)
    return SimpleNamespace(state=dict(state))


def test_get_confluence_report_no_context():
    ctx = _make_tool_context(None)
    result = get_confluence_report(tool_context=ctx)

    assert result["has_signals"] is False
    assert result["tickers"] == []
    assert result["status"] == "NO_CONTEXT"


def test_get_confluence_report_empty_state():
    ctx = _make_tool_context({"confluence_reports": {}, "candidates": []})
    result = get_confluence_report(tool_context=ctx)

    assert result["has_signals"] is False
    assert result["tickers"] == []
    assert result["status"] == "EMPTY_CONFLUENCE"


def test_get_confluence_report_populated_state_merges_tickers():
    ctx = _make_tool_context({
        "candidates": [
            {"ticker": "gs", "net_buy_activity": 250000},
            {"ticker": "AMAT", "net_buy_activity": 120000},
        ],
        "confluence_reports": {
            "GS": {
                "gov_contracts_spend_usd": 15_000_000.0,
                "form4_signal": "Cluster Buy",
                "lobbying_spend_usd": 450_000.0,
            },
            "TSM": {
                "gov_contracts_spend_usd": 0.0,
                "form4_signal": "Moderate",
                "lobbying_spend_usd": 120_000.0,
            },
        },
    })

    result = get_confluence_report(tool_context=ctx)

    assert result["has_signals"] is True
    assert result["status"] == "OK"
    assert result["tickers"] == ["GS", "AMAT", "TSM"]
    assert result["confluence_reports"]["GS"]["form4_signal"] == "Cluster Buy"


@patch("congress_trades_agent.skills.congress_trader.tools.fetch_fmp_fundamentals")
def test_get_fundamentals_tool_wraps_pydantic(mock_fetch):
    mock_fetch.return_value = {
        "ticker": "MSFT",
        "pe_ratio": 28.0,
        "price": 300.0,
        "forward_pe": 25.0,
        "debt_to_equity": 0.8,
        "free_cash_flow_yield": 0.03,
        "return_on_equity": 0.35,
        "valuation_verdict": "FAIRLY_VALUED",
        "fundamental_health_score": 70.0,
        "error": None,
    }

    result = get_fundamentals("msft")

    assert isinstance(result, FundamentalEvaluation)
    assert result.ticker == "MSFT"
    assert result.valuation_verdict == "FAIRLY_VALUED"
    assert result.price == 300.0
    mock_fetch.assert_called_once_with("msft")


@patch("congress_trades_agent.skills.congress_trader.tools.execute_store_decision")
def test_store_trade_decision_tool_success(mock_execute_store):
    """Test that the store_trade_decision tool correctly packages inputs and calls the underlying script."""
    mock_execute_store.return_value = None

    test_ticker = "nvda"
    result = store_trade_decision(
        ticker=test_ticker,
        action="BUY",
        conviction_score=85.0,
        pe_ratio=32.5,
        valuation_verdict="UNDERVALUED",
        fundamental_health_score=85.0,
        congressional_net_buys=3,
        insider_cluster_buy=True,
        price=300.0,
        synthesis_summary="Strong congressional backing and bullish insider activity.",
    )

    assert "Successfully validated and stored decision record" in result
    mock_execute_store.assert_called_once()

    _, kwargs = mock_execute_store.call_args
    assert kwargs["ticker"] == test_ticker.upper()
    assert kwargs["action"] == "BUY"
    assert kwargs["entry_price"] == 300.0
    assert kwargs["conviction_score"] == 85.0


@patch("congress_trades_agent.skills.congress_trader.tools.execute_fetch_decisions")
def test_fetch_historical_episodes_tool_success(mock_execute_fetch):
    """Test that fetch_historical_episodes unpacks the row iterator into structured dictionaries."""
    mock_row = MagicMock()
    mock_row.decision_id = "dec-NVDA-1776892300"
    mock_row.ticker = "NVDA"
    mock_row.decision_timestamp = "2026-10-20T21:00:00Z"
    mock_row.action = "BUY"
    mock_row.conviction_score = 90.0
    mock_row.decision_snapshot_json = {"ticker": "NVDA", "fundamentals": {"pe_ratio": 32.5}}

    mock_execute_fetch.return_value = [mock_row]

    results = fetch_historical_episodes(
        ticker="nvda",
        valuation_verdict="UNDERVALUED",
        min_conviction=80.0,
        limit=3,
    )

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["ticker"] == "NVDA"
    assert results[0]["conviction_score"] == 90.0
    assert results[0]["decision_snapshot"]["fundamentals"]["pe_ratio"] == 32.5


@patch("congress_trades_agent.skills.congress_trader.tools.calculate_trailing_return")
def test_get_trailing_return_wrapper(mock_calculate):
    mock_calculate.return_value = {
        "ticker": "AAPL",
        "entry_date": "2026-06-01",
        "entry_price": 100.0,
        "current_price": 150.0,
        "trailing_return_pct": 50.0,
    }

    result = get_trailing_return("AAPL", "2026-06-01", entry_price=100.0)

    mock_calculate.assert_called_once_with("AAPL", "2026-06-01", 100.0)
    assert result["ticker"] == "AAPL"
    assert result["trailing_return_pct"] == 50.0