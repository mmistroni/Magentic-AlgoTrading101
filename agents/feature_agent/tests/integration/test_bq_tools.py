from feature_agent.tools import fetch_consensus_holdings_tool
from datetime import date

def test_fetch_consensus_holding_tool():
    start_date = date(2025, 12, 1)
    end_date = date(2025,12, 22)
    res = get_latest_prices_fmp('AAPL', start_date, end_date)
    print(f'---- Result is \n{res}')