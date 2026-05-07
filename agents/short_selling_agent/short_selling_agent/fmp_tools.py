# fmp_tools.py
# Agent-first, no caching, fresh FMP calls only
# Returns pure JSON (dict/list)

import requests
import pandas as pd
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
import os
import time#
import ta

# -----------------------------
# CONFIGURATION
# -----------------------------
FMP_API_KEY = os.getenv('FMP_API_KEY', 'YOUR_KEY_HERE')  # Set in environment
BASE_URL = 'https://financialmodelingprep.com/api/v3'

# Rate limiting: 1 sec delay to stay under 60/min
REQUEST_DELAY = 1.0

# -----------------------------
# HELPER: Simple GET (No Cache)
# -----------------------------
def _get(url: str) -> Dict:
    try:
        response = requests.get(url, timeout=10)
        time.sleep(REQUEST_DELAY)  # Rate limit
        return response.json() if response.status_code == 200 else {}
    except Exception as e:
        print(f"Request failed: {str(e)}")
        return {}


# -----------------------------
# 1. OHLCV → list[dict]
# -----------------------------
def get_historical_price_full(symbol: str, limit: int = 365) -> List[Dict]:
    url = f"{BASE_URL}/historical-price-full/{symbol}?apikey={FMP_API_KEY}"
    data = _get(url)
    if not data or 'historical' not in data:
        return []
    return [{**day, 'date': str(day['date'])} for day in data['historical'][:limit]]


# -----------------------------
# 2. Technical Indicators → list[dict] (uses pandas temporarily)
# -----------------------------
# Replace in fmp_tools.py

def get_technical_indicators(
    symbol: str,
    indicator_type: str,
    period_length: int = 14,
    from_date: Optional[str] = None,
    to_date: Optional[str] = None
) -> List[Dict]:
    """
    Uses `ta` package instead of `talib` → no install issues on Linux/Docker/Dataflow.
    Returns list[dict] with 'date', 'value'.
    """
    try:
        import ta
    except ImportError:
        print("Error: `ta` not installed. Run: pip install ta")
        return []

    ohlcv_list = get_historical_price_full(symbol, limit=500)
    if len(ohlcv_list) < period_length:
        return []

    df = pd.DataFrame(ohlcv_list)
    df['date'] = pd.to_datetime(df['date'])
    df = df.sort_values('date').reset_index(drop=True)

    if from_date and to_date:
        start = pd.to_datetime(from_date)
        end = pd.to_datetime(to_date)
        df = df[(df['date'] >= start) & (df['date'] <= end)]

    if df.empty or len(df) < period_length:
        return []

    try:
        result = []

        if indicator_type == 'rsi':
            df['rsi'] = ta.momentum.RSIIndicator(df['adjClose'], window=period_length).rsi()
            result = [{'date': d.strftime('%Y-%m-%d'), 'value': float(v) if not pd.isna(v) else None}
                     for d, v in zip(df['date'], df['rsi'])]

        elif indicator_type == 'adx':
            df['adx'] = ta.trend.ADXIndicator(
                df['high'], df['low'], df['close'], window=period_length
            ).adx()
            result = [{'date': d.strftime('%Y-%m-%d'), 'value': float(v) if not pd.isna(v) else None}
                     for d, v in zip(df['date'], df['adx'])]

        elif indicator_type == 'sma':
            df['sma'] = df['adjClose'].rolling(period_length).mean()
            result = [{'date': d.strftime('%Y-%m-%d'), 'value': float(v) if not pd.isna(v) else None}
                     for d, v in zip(df['date'], df['sma'])]

        elif indicator_type == 'bollinger_upper':
            indicator = ta.volatility.BollingerBands(df['adjClose'], window=20, window_dev=2)
            df['bollinger_upper'] = indicator.bollinger_hband()
            result = [{'date': d.strftime('%Y-%m-%d'), 'value': float(v) if not pd.isna(v) else None}
                     for d, v in zip(df['date'], df['bollinger_upper'])]

        elif indicator_type == 'bollinger_lower':
            indicator = ta.volatility.BollingerBands(df['adjClose'], window=20, window_dev=2)
            df['bollinger_lower'] = indicator.bollinger_lband()
            result = [{'date': d.strftime('%Y-%m-%d'), 'value': float(v) if not pd.isna(v) else None}
                     for d, v in zip(df['date'], df['bollinger_lower'])]

        else:
            print(f"Indicator {indicator_type} not supported.")
            return []

        return result

    except Exception as e:
        print(f"Error computing {indicator_type} for {symbol}: {str(e)}")
        return []

# -----------------------------
# 3. Short Interest → dict
# -----------------------------
def get_short_interest(symbol: str) -> Dict[str, Any]:
    url = f"{BASE_URL}/short-interest/{symbol}?apikey={FMP_API_KEY}"
    data = _get(url)
    if isinstance(data, list) and len(data) > 0:
        d = data[0]
        return {
            'shortDate': str(d.get('date')) if d.get('date') else None,
            'shortInterest': float(d['shortInterest']) if d.get('shortInterest') else None,
            'shortPercent': float(d['shortPercentFloat']) if d.get('shortPercentFloat') else None
        }
    return {'shortDate': None, 'shortInterest': None, 'shortPercent': None}


# -----------------------------
# 4. Historical Earnings → list[dict]
# -----------------------------
def get_historical_earnings(from_date: str, to_date: str) -> List[Dict]:
    url = f"{BASE_URL}/historical/earning_calendar?from={from_date}&to={to_date}&apikey={FMP_API_KEY}"
    data = _get(url)
    if not isinstance(data, list):
        return []

    results = []
    for e in data:
        try:
            eps = float(e['eps']) if e['eps'] else None
            est = float(e['estimate']) if e['estimate'] else None
            surprise = (eps - est) / est if est and eps is not None else None
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
# 5. Company Profile → dict
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
# 6. BULK: Get ALL Data for One Ticker (✅ Agent Entry Point)
# -----------------------------
def get_all_data_for_ticker(
    symbol: str,
    as_of_date: Optional[str] = None,
    days_back: int = 365
) -> Dict:
    """
    Fetch ALL data for this symbol as-of a historical date.
    Used for backtesting: simulate what was known on that day.
    """
    if as_of_date is None:
        as_of_date = datetime.now().strftime('%Y-%m-%d')

    end_date = pd.to_datetime(as_of_date)
    start_date = (end_date - timedelta(days=days_back)).strftime('%Y-%m-%d')

    earnings = get_historical_earnings(start_date, as_of_date)
    symbol_earnings = [e for e in earnings if e['symbol'] == symbol]

    return {
        "symbol": symbol,
        "as_of_date": as_of_date,

        "price": get_historical_price_full(symbol, limit=days_back),

        "indicators": {
            "rsi": get_technical_indicators(symbol, "rsi", 14, start_date, as_of_date),
            "adx": get_technical_indicators(symbol, "adx", 14, start_date, as_of_date),
            "sma200": get_technical_indicators(symbol, "sma", 200, start_date, as_of_date),
            "sma50": get_technical_indicators(symbol, "sma", 50, start_date, as_of_date),
            "sma20": get_technical_indicators(symbol, "sma", 20, start_date, as_of_date),
            "bollinger_upper": get_technical_indicators(symbol, "bollinger_upper", 20, start_date, as_of_date),
            "bollinger_lower": get_technical_indicators(symbol, "bollinger_lower", 20, start_date, as_of_date),
        },

        "fundamentals": {
            "short_interest": get_short_interest(symbol),
            "recent_earnings": symbol_earnings,
            "profile": get_company_profile(symbol)
        }
    }