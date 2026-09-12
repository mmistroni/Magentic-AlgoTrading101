import pytest
from unittest.mock import patch

from congress_trades_agent.skills.congress_researcher.tools import (
    fetch_congress_signals,
    fetch_contract_signals,
)
from congress_trades_agent.schemas import (
    CongressSignalsResponse,
    ContractSignalsResponse,
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


@patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_data")
@patch("congress_trades_agent.skills.congress_researcher.tools.get_bq_signals_data")
def test_congress_researcher_skill_tool_sequence(
    mock_get_contracts, mock_get_congress, mock_congress_records, mock_contract_records
):
    """Verifies tool execution workflow across Congress and Contract data pipelines."""
    mock_get_congress.return_value = mock_congress_records
    mock_get_contracts.return_value = mock_contract_records

    # Step 1: Congress tool retrieves political candidates
    res_congress = fetch_congress_signals(analysis_date="2026-06-30")
    assert isinstance(res_congress, CongressSignalsResponse)
    assert res_congress.count == 1
    assert res_congress.signals[0].ticker == "LMT"
    mock_get_congress.assert_called_once_with("2026-06-30")

    # Step 2: Contract tool cross-references candidates
    flagged_ticker = res_congress.signals[0].ticker
    res_contracts = fetch_contract_signals(ticker=flagged_ticker, analysis_date="2026-06-30")
    assert isinstance(res_contracts, ContractSignalsResponse)
    assert res_contracts.ticker == "LMT"
    assert res_contracts.total_contract_spend_usd == 75000000.0
    mock_get_contracts.assert_called_once_with(ticker="LMT", analysis_date="2026-06-30")