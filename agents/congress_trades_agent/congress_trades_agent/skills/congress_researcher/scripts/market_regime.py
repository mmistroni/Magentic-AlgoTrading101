import os
import requests
import pandas as pd
import yfinance as yf
from typing import Optional
from functools import lru_cache
from google.cloud import bigquery


import os
import requests
import pandas as pd
import yfinance as yf
from datetime import date, datetime
from typing import Optional, Union
from functools import lru_cache
from google.cloud import bigquery


def check_market_regime(
    row_date: Union[str, date, pd.Timestamp], 
    context_date_str: str
) -> bool:
    """Checks if SPX/SPY was in an uptrend on a specific signal date relative to SMA200.

    Args:
        row_date: The specific trade/signal date (date object, Timestamp, or ISO string).
        context_date_str: Analysis end date string (e.g. '2026-06-30').
    """
    try:
        spy_data = _get_spy_data(str(context_date_str))
        if spy_data.empty:
            return True

        # Guarantee row_date is a timezone-naive Timestamp
        target_date = pd.to_datetime(row_date).tz_localize(None)
        
        idx_loc = spy_data.index.get_indexer([target_date], method='pad')[0]

        if idx_loc == -1: 
            return True

        price = spy_data.iloc[idx_loc]['adjClose']
        sma = spy_data.iloc[idx_loc]['SMA200']

        if pd.isna(sma):
            return True

        return bool(price > sma)

    except Exception as e:
        print(f"⚠️ Regime Check Warning: {e}")
        return True


@lru_cache(maxsize=32)
def _get_spy_data(end_date_str: str) -> pd.DataFrame:
    try:
        fmp_api_key = os.environ.get('FMP_API_KEY')
        if not fmp_api_key:
            return pd.DataFrame()

        spx_url = f"https://financialmodelingprep.com/api/v3/historical-price-full/^SPX?from=2022-01-01&to={end_date_str}&apikey={fmp_api_key}"
        response = requests.get(spx_url, timeout=10)
        
        if response.status_code != 200:
            return pd.DataFrame()
            
        spx_res = response.json().get('historical', [])
        if not spx_res:
            return pd.DataFrame()

        spx_res = spx_res[::-1]
        spy_data = pd.DataFrame(data=spx_res)
        
        spy_data['date'] = pd.to_datetime(spy_data['date'])
        spy_data.set_index('date', inplace=True)
        spy_data.index = spy_data.index.tz_localize(None)
        spy_data['SMA200'] = spy_data['adjClose'].rolling(window=200).mean()
        
        return spy_data
        
    except Exception as e:
        print(f"❌ SPY Data Fetch Error: {e}")
        return pd.DataFrame()

    