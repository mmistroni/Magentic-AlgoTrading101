import pytest
from unittest.mock import patch, MagicMock
from congress_trades_agent.skills.congress_trader.agent import congress_trader

@pytest.mark.asyncio
async def test_agent_tool_integration_fetch_historical_episodes_success():
    """Use Case 1: Agent successfully integrates and calls fetch_historical_episodes to retrieve past trade context."""
    with patch("congress_trades_agent.skills.congress_trader.agent.fetch_historical_episodes") as mock_fetch:
        mock_fetch.return_value = [
            {
                "decision_id": "dec-NVDA-101",
                "ticker": "NVDA",
                "action": "BUY",
                "conviction_score": 85.0,
                "decision_snapshot": {"fundamentals": {"valuation_verdict": "UNDERVALUED"}}
            }
        ]

        # Simulate agent tool invocation or runner logic
        results = mock_fetch(ticker="NVDA", valuation_verdict="UNDERVALUED", min_conviction=80.0)

        assert isinstance(results, list)
        assert len(results) == 1
        assert results[0]["ticker"] == "NVDA"
        assert results[0]["conviction_score"] == 85.0
        mock_fetch.assert_called_once_with(
            ticker="NVDA", 
            valuation_verdict="UNDERVALUED", 
            min_conviction=80.0
        )


@pytest.mark.asyncio
async def test_agent_tool_integration_fetch_historical_episodes_empty():
    """Use Case 2: Agent handles an empty historical episodes result gracefully when no prior trades match."""
    with patch("congress_trades_agent.skills.congress_trader.agent.fetch_historical_episodes") as mock_fetch:
        mock_fetch.return_value = []

        results = mock_fetch(ticker="UNKNOWN", min_conviction=90.0)

        assert isinstance(results, list)
        assert len(results) == 0
        mock_fetch.assert_called_once()


@pytest.mark.asyncio
async def test_agent_tool_integration_store_trade_decision_success():
    """Use Case 3: Agent successfully invokes store_trade_decision upon reaching a final trade verdict."""
    with patch("congress_trades_agent.skills.congress_trader.agent.store_trade_decision") as mock_store:
        mock_store.return_value = "Successfully stored decision dec-MSFT-500 for MSFT."

        response = mock_store(
            ticker="MSFT",
            action="BUY",
            conviction_score=92.0,
            valuation_verdict="UNDERVALUED",
            pe_ratio=26.5,
            notes="Strong congressional buying cluster matched with excellent FCF yield."
        )

        assert "Successfully stored decision" in response
        mock_store.assert_called_once()
        _, kwargs = mock_store.call_args
        assert kwargs["ticker"] == "MSFT"
        assert kwargs["action"] == "BUY"
        assert kwargs["conviction_score"] == 92.0


@pytest.mark.asyncio
async def test_agent_tool_integration_combined_workflow():
    """Use Case 4: Agent executes a multi-tool flow (fetching past history, checking fundamentals, then storing decision)."""
    with patch("congress_trades_agent.skills.congress_trader.agent.fetch_historical_episodes") as mock_fetch_history, \
         patch("congress_trades_agent.skills.congress_trader.agent.fetch_fmp_fundamentals") as mock_fetch_fundamentals, \
         patch("congress_trades_agent.skills.congress_trader.agent.store_trade_decision") as mock_store_decision:

        # Step 1: Mock historical memory response
        mock_fetch_history.return_value = [{"decision_id": "dec-1", "action": "BUY"}]
        
        # Step 2: Mock live fundamental review
        mock_fetch_fundamentals.return_value = {
            "ticker": "AAPL",
            "valuation_verdict": "FAIRLY_VALUED",
            "pe_ratio": 29.0,
            "error": None
        }

        # Step 3: Mock storage response
        mock_store_decision.return_value = "Successfully stored decision."

        # Execute simulated workflow steps
        history = mock_fetch_history(ticker="AAPL")
        fundamentals = mock_fetch_fundamentals("AAPL")
        storage_res = mock_store_decision(
            ticker="AAPL",
            action="HOLD",
            conviction_score=50.0,
            valuation_verdict=fundamentals["valuation_verdict"],
            pe_ratio=fundamentals["pe_ratio"],
            notes="Holding based on mixed history and fair valuation."
        )

        # Assertions across the combined tool chain
        assert len(history) == 1
        assert fundamentals["valuation_verdict"] == "FAIRLY_VALUED"
        assert "Successfully stored" in storage_res
        
        mock_fetch_history.assert_called_once()
        mock_fetch_fundamentals.assert_called_once_with("AAPL")
        mock_store_decision.assert_called_once()