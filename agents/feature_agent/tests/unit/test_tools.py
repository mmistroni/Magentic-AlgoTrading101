from feature_agent.tools import get_latest_prices_fmp
from datetime import date

# mock bq client to test the other method too


def test_get_latest_price_fmp():
    start_date = date(2025, 12, 1)
    end_date = date(2025,12, 22)
    res = get_latest_prices_fmp('AAPL', start_date, end_date)
    print(f'---- Result is \n{res}')