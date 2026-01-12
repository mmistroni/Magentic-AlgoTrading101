from feature_agent.tools import fetch_consensus_holdings_tool
from datetime import date

def test_fetch_consensus_holding_tool():
    filing_date = '2024-12-31'
    res = fetch_consensus_holdings_tool(filing_date)
    assert len(res) > 0
    