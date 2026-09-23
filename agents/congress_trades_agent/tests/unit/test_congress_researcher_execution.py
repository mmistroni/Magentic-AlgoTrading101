from unittest.mock import MagicMock, patch
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


@pytest.fixture
def mock_congress_records():
    return [{
        "ticker": "LMT",
        "signal_date": "2026-06-15",
        "purchase_count": 3,
        "sale_count": 0,
        "net_buy_activity": 3,
        "buying_days_count": 2,
        "last_trade_date": "2026-06-20",
        "market_uptrend": True,
    }]


@pytest.fixture
def mock_contract_records():
    return [{
        "action_date": "2026-05-10",
        "recipient_name": "LOCKHEED MARTIN CORP",
        "ticker": "LMT",
        "amount": 75000000.0,
        "agency": "DEPT OF DEFENSE",
        "description": "F-35 Logistics Support",
    }]


@pytest.fixture
def mock_tool_context():
    context = MagicMock(spec=ToolContext)
    context.state = {
        "candidates": [],
        "confluence_reports": {},
    }
    return context


def test_fetch_congress_signals_updates_context(mock_congress_records, mock_tool_context):
    """Tests fetch_congress_signals independently and verifies state updates."""
    with patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_data") as mock_bq, \
         patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_signals_data", mock_bq):
        
        mock_bq.return_value = mock_congress_records

        res = fetch_congress_signals(analysis_date="2026-06-30", tool_context=mock_tool_context)

        assert isinstance(res, CongressSignalsResponse)
        assert res.count == 1
        assert res.signals[0].ticker == "LMT"

        # Assert candidate record containing 'LMT' was stored in state
        candidates = mock_tool_context.state["candidates"]
        assert len(candidates) > 0
        assert any(
            (c.ticker if hasattr(c, "ticker") else c.get("ticker")) == "LMT"
            for c in candidates
        )


def test_fetch_contract_signals_updates_context(mock_contract_records, mock_tool_context):
    """Tests fetch_contract_signals independently and verifies state updates."""
    with patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_data") as mock_bq, \
         patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_signals_data", mock_bq):
        
        mock_bq.return_value = mock_contract_records

        res = fetch_contract_signals(ticker="LMT", analysis_date="2026-06-30", tool_context=mock_tool_context)

        assert isinstance(res, ContractSignalsResponse)
        assert res.ticker == "LMT"
        assert res.total_contract_spend_usd == 75000000.0
        assert "LMT" in mock_tool_context.state["confluence_reports"]

