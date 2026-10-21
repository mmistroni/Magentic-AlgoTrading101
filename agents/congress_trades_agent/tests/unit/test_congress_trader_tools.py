from unittest.mock import patch, MagicMock
from congress_trades_agent.skills.congress_trader.tools import (
    get_fundamentals,
    store_trade_decision,
    fetch_historical_episodes
)
from congress_trades_agent.schemas import FundamentalEvaluation

@patch("congress_trades_agent.skills.congress_trader.tools.fetch_fmp_fundamentals")
def test_get_fundamentals_tool_wraps_pydantic(mock_fetch):
    mock_fetch.return_value = {
        "ticker": "MSFT",
        "pe_ratio": 28.0,
        "forward_pe": 25.0,
        "debt_to_equity": 0.8,
        "free_cash_flow_yield": 0.03,
        "return_on_equity": 0.35,
        "valuation_verdict": "FAIRLY_VALUED",
        "fundamental_health_score": 70.0,
        "error": None
    }

    result = get_fundamentals("msft")
    
    assert isinstance(result, FundamentalEvaluation)
    assert result.ticker == "MSFT"
    assert result.valuation_verdict == "FAIRLY_VALUED"
    mock_fetch.assert_called_once_with("msft")


@patch("congress_trades_agent.skills.congress_trader.tools.execute_store_decision")
def test_store_trade_decision_tool_success(mock_execute_store):
    """Test that the store_trade_decision tool correctly packages inputs and calls the underlying script."""
    mock_execute_store.return_value = None  # Executes successfully without error

    result = store_trade_decision(
        ticker="nvda",
        action="BUY",
        conviction_score=85.0,
        valuation_verdict="UNDERVALUED",
        pe_ratio=32.5,
        notes="Strong congressional backing and bullish insider activity."
    )

    assert "Successfully stored decision" in result
    mock_execute_store.assert_called_once()
    
    # Verify the positional/keyword arguments passed down to the executor script
    _, kwargs = mock_execute_store.call_args
    assert kwargs["ticker"] == "nvda"
    assert kwargs["action"] == "BUY"
    assert kwargs["conviction_score"] == 85.0


@patch("congress_trades_agent.skills.congress_trader.tools.execute_fetch_decisions")
def test_fetch_historical_episodes_tool_success(mock_execute_fetch):
    """Test that fetch_historical_episodes unpacks the row iterator into structured dictionaries."""
    # Mock a BigQuery Row-like object
    mock_row = MagicMock()
    mock_row.decision_id = "dec-NVDA-1776892300"
    mock_row.ticker = "NVDA"
    mock_row.decision_timestamp = "2026-10-20T21:00:00Z"
    mock_row.action = "BUY"
    mock_row.conviction_score = 90.0
    mock_row.decision_snapshot = {"ticker": "NVDA", "fundamentals": {"pe_ratio": 32.5}}

    mock_execute_fetch.return_value = [mock_row]

    results = fetch_historical_episodes(
        ticker="nvda",
        valuation_verdict="UNDERVALUED",
        min_conviction=80.0,
        limit=3
    )

    assert isinstance(results, list)
    assert len(results) == 1
    assert results[0]["ticker"] == "NVDA"
    assert results[0]["conviction_score"] == 90.0
    assert results[0]["decision_snapshot"]["fundamentals"]["pe_ratio"] == 32.5
    
    mock_execute_fetch.assert_called_once_with(
        ticker="nvda",
        valuation_verdict="UNDERVALUED",
        min_conviction=80.0,
        limit=3
    )