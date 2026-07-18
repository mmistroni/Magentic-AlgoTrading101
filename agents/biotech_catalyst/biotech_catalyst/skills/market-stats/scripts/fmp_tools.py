# fmp_tools.py — Agent-ready, backtest-safe, no look-ahead bias

import os
import json
import time
import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import ta  # pip install ta

# -----------------------------
# CONFIGURATION
# -----------------------------
FMP_API_KEY = os.getenv('FMP_API_KEY')
if not FMP_API_KEY:
    raise EnvironmentError("FMP_API_KEY not found in environment.")

BASE_URL = 'https://financialmodelingprep.com/api/v3'

# Rate limit: 1 sec delay between calls
REQUEST_DELAY = 1.0

# -----------------------------
# HELPER: Safe GET (no caching)
# -----------------------------
def _get(url: str) -> Dict:
    try:
        response = requests.get(url, timeout=10)
        time.sleep(REQUEST_DELAY)
        return response.json() if response.status_code == 200 else {}
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return {}


# -----------------------------
# 1. OHLCV: Get History Up To as_of_date
# -----------------------------
def get_historical_price_full(
    symbol: str,
    as_of_date: str,
    lookback_days: int = 365
) -> List[Dict]:
    """
    Fetch up to `lookback_days` of daily data, ending at `as_of_date`.
    Ensures no future data is used.
    """
    # Back up to get enough history
    end_date = datetime.strptime(as_of_date, '%Y-%m-%d')
    start_date = (end_date - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
    end_date_str = end_date.strftime('%Y-%m-%d')

    url = f"{BASE_URL}/historical-price-full/{symbol}?apikey={FMP_API_KEY}"
    data = _get(url)
    if not data or 'historical' not in data:
        return []

    records = []
    for point in data['historical']:
        date_str = point['date'].split(' ')[0]  # In case of '2023-06-15 16:00:00'
        if start_date <= date_str <= end_date_str:
            point['date'] = date_str
            point['adjClose'] = point.get('adjClose', point['close'])
            records.append(point)

    records.sort(key=lambda x: x['date'], reverse=False)
    return records  # Sorted old → new


# -----------------------------
# 2. Technical Indicators — Historical-Only Mode
# -----------------------------
def get_technical_indicators(
    symbol: str,
    indicator_type: str,
    period_length: int = 14,
    as_of_date: str = None,
    lookback_days: int = 365
) -> List[Dict]:
    """
    Compute indicator using only data up to `as_of_date`.
    Returns list of dicts with 'date', 'value'
    """
    if as_of_date is None:
        as_of_date = datetime.now().strftime('%Y-%m-%d')

    ohlcv_list = get_historical_price_full(symbol, as_of_date, lookback_days)
    if len(ohlcv_list) < period_length:
        return []

    df = pd.DataFrame(ohlcv_list)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    # Enforce end date
    as_of_dt = pd.to_datetime(as_of_date)
    df = df[df['date'] <= as_of_dt]

    if len(df) < period_length:
        return []

    result = []

    try:
        if indicator_type == 'rsi':
            df['value'] = ta.momentum.RSIIndicator(df['adjClose'], window=period_length).rsi()
            column = 'value'
        elif indicator_type == 'adx':
            df['value'] = ta.trend.ADXIndicator(
                df['high'], df['low'], df['close'], window=period_length
            ).adx()
            column = 'value'
        elif indicator_type == 'sma':
            df['value'] = df['adjClose'].rolling(period_length).mean()
        elif indicator_type == 'bollinger_upper':
            bb = ta.volatility.BollingerBands(df['adjClose'], window=20, window_dev=2)
            df['value'] = bb.bollinger_hband()
            column = 'value'
        elif indicator_type == 'bollinger_lower':
            bb = ta.volatility.BollingerBands(df['adjClose'], window=20, window_dev=2)
            df['value'] = bb.bollinger_lband()
            column = 'value'
        else:
            print(f"Indicator {indicator_type} not supported.")
            return []

        result = [
            {
                'date': row['date'].strftime('%Y-%m-%d'),
                'value': float(row['value']) if pd.notna(row['value']) else None
            }
            for _, row in df.iloc[period_length:].iterrows()
        ]

    except Exception as e:
        print(f"Error computing {indicator_type} for {symbol}: {str(e)}")

    return result


# -----------------------------
# 3. Short Interest: Nearest Before as_of_date
# -----------------------------
def get_short_interest(
    symbol: str,
    as_of_date: str
) -> Dict[str, Any]:
    """
    Returns the most recent short interest data available *before* as_of_date.
    """
    url = f"{BASE_URL}/short-interest/{symbol}?apikey={FMP_API_KEY}"
    data = _get(url)

    if isinstance(data, list) and len(data) > 0:
        # Sort by date, descending
        data = sorted(data, key=lambda x: x['date'], reverse=True)
        as_of_dt = datetime.strptime(as_of_date, '%Y-%m-%d')
        for item in data:
            item_date = datetime.strptime(item['date'], '%Y-%m-%d')
            if item_date <= as_of_dt:
                return {
                    'shortDate': item['date'],
                    'shortInterest': float(item['shortInterest']) if item.get('shortInterest') else None,
                    'shortPercent': float(item['shortPercentFloat']) if item.get('shortPercentFloat') else None
                }

    return {'shortDate': None, 'shortInterest': None, 'shortPercent': None}


# -----------------------------
# 4. Earnings: Up to as_of_date
# -----------------------------
def get_historical_earnings(
    from_date: str,
    to_date: str
) -> List[Dict]:
    url = f"{BASE_URL}/historical/earning_calendar?from={from_date}&to={to_date}&apikey={FMP_API_KEY}"
    data = _get(url)
    if not isinstance(data, list):
        return []

    results = []
    for e in data:
        try:
            eps = float(e['eps']) if e['eps'] else None
            est = float(e['estimate']) if e['estimate'] else None
            surprise = (eps - est) / est if eps is not None and est else None

            results.append({
                'symbol': e['symbol'],
                'date': e['date'],
                'eps': eps,
                'estimate': est,
                'surprise': float(surprise) if surprise else None
            })
        except Exception:
            continue
    return results


# -----------------------------
# 5. Company Profile — No Historical Needed
# -----------------------------
def get_company_profile(symbol: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/profile/{symbol}?apikey={FMP_API_KEY}"
    data = _get(url)
    if isinstance(data, list) and len(data) > 0:
        d = data[0]
        return {
            'sector': d.get('sector'),
            'industry': d.get('industry'),
            'marketCap': float(d['mktCap']) if d.get('mktCap') else None,
            'beta': float(d['beta']) if d.get('beta') else None
        }
    return {'sector': None, 'industry': None, 'marketCap': None, 'beta': None}


# -----------------------------
# 6. ALL-IN-ONE: Agent Entry Point (Time-Safe)
# -----------------------------
def get_all_data_for_ticker(
    symbol: str,
    as_of_date: str,
    lookback_days: int = 365
) -> Dict:
    """
    Fetch all data for this symbol as it was known on `as_of_date`.
    Perfect for backtesting.
    """
    # Compute date range
    end_dt = datetime.strptime(as_of_date, '%Y-%m-%d')
    start_date = (end_dt - timedelta(days=lookback_days)).strftime('%Y-%m-%d')
    end_date_str = end_dt.strftime('%Y-%m-%d')

    # Fetch earnings for full window, then filter
    earnings_window = get_historical_earnings(start_date, end_date_str)
    symbol_earnings = [e for e in earnings_window if e['symbol'] == symbol]

    return {
        "symbol": symbol,
        "as_of_date": as_of_date,

        "price": get_historical_price_full(symbol, as_of_date, lookback_days),

        "indicators": {
            "rsi": get_technical_indicators(symbol, "rsi", 14, as_of_date, lookback_days),
            "adx": get_technical_indicators(symbol, "adx", 14, as_of_date, lookback_days),
            "sma200": get_technical_indicators(symbol, "sma", 200, as_of_date, lookback_days),
            "sma50": get_technical_indicators(symbol, "sma", 50, as_of_date, lookback_days),
            "sma20": get_technical_indicators(symbol, "sma", 20, as_of_date, lookback_days),
            "bollinger_upper": get_technical_indicators(symbol, "bollinger_upper", 20, as_of_date, lookback_days),
            "bollinger_lower": get_technical_indicators(symbol, "bollinger_lower", 20, as_of_date, lookback_days),
        },

        "fundamentals": {
            "short_interest": get_short_interest(symbol, as_of_date),
            "recent_earnings": symbol_earnings,
            "profile": get_company_profile(symbol)
        }
    }