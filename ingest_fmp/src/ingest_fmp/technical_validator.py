import time
import logging
import requests
import numpy as np
import pandas as pd
from ta.volume import OnBalanceVolumeIndicator, ChaikinMoneyFlowIndicator
from ta.momentum import AwesomeOscillatorIndicator
from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

class BaseTechnicalValidator:
    """Base class to share common SMA fetching, historical data fetching, and throttling logic."""
    def __init__(self, client: FMPClient, throttle_seconds: int = 5):
        self.client = client
        self.throttle_seconds = throttle_seconds

    def _get_symbol(self, symbol_dict: dict) -> str:
        """Helper to safely retrieve the ticker/symbol from the dictionary."""
        return symbol_dict.get('symbol') or symbol_dict.get('ticker', '')

    def _fetch_sma(self, symbol: str, period: int) -> dict | None:
        """Fetches SMA data with built-in throttling and error safety."""
        try:
            data = self.client.get_sma(symbol=symbol, period_length=period, timeframe="1day")
            time.sleep(self.throttle_seconds)
            if data and isinstance(data, list) and len(data) > 0:
                return data[0]
        except Exception as e:
            logger.error(f"Error fetching SMA{period} for {symbol}: {str(e)}")
            time.sleep(self.throttle_seconds)
        return None

    def _fetch_historical_data(self, symbol: str) -> list:
        """Fetches full historical price/volume data for TA indicator calculations."""
        try:
            # Assumes FMPClient has an api_key attribute or we can call the historical endpoint via client/requests
            api_key = getattr(self.client, "api_key", None)
            if not api_key:
                return []
            hist_url = f'https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}?apikey={api_key}'
            r = requests.get(hist_url, timeout=10)
            if r.status_code == 200:
                return r.json().get('historical', [])
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
        return []

    def _compute_ta_indicators(self, symbol: str) -> dict:
        """Computes OBV, CMF, Choppiness, DeMarker, and EWO using `ta` and `pandas`."""
        try:
            raw_history = self._fetch_historical_data(symbol)
            if not raw_history or not isinstance(raw_history, list):
                return {}

            df = pd.DataFrame(raw_history)
            if df.empty or 'close' not in df.columns or 'volume' not in df.columns:
                return {}

            # Ensure chronological order
            df = df.iloc[::-1].reset_index(drop=True)

            # 1. OBV & CMF
            df['obv'] = OnBalanceVolumeIndicator(close=df['close'], volume=df['volume']).on_balance_volume()
            df['cmf'] = ChaikinMoneyFlowIndicator(high=df['high'], low=df['low'], close=df['close'], volume=df['volume']).chaikin_money_flow()

            # 2. Choppiness & DeMarker
            window = 14
            high_low = df['high'] - df['low']
            high_close = np.abs(df['high'] - df['close'].shift(1))
            low_close = np.abs(df['low'] - df['close'].shift(1))
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            tr_sum = tr.rolling(window=window).sum()
            max_h = df['high'].rolling(window=window).max()
            min_l = df['low'].rolling(window=window).min()
            df['choppiness'] = 100 * (np.log10(tr_sum / (max_h - min_l)) / np.log10(window))

            high_diff = df['high'] - df['high'].shift(1)
            demax = high_diff.where(high_diff > 0, 0.0)
            low_diff = df['low'].shift(1) - df['low']
            demin = low_diff.where(low_diff > 0, 0.0)
            df['demarker'] = demax.rolling(window=window).mean() / (demax.rolling(window=window).mean() + demin.rolling(window=window).mean())

            last = df.iloc[-1]
            prev = df.iloc[-2] if len(df) > 1 else last

            return {
                'previous_obv': prev.get('obv'),
                'current_obv': last.get('obv'),
                'obv_historical': df['obv'].dropna().tolist()[-20:],
                'previous_cmf': prev.get('cmf'),
                'current_cmf': last.get('cmf'),
                'cmf_historical': df['cmf'].dropna().tolist()[-20:],
                'choppiness': last.get('choppiness'),
                'demarker': last.get('demarker'),
                'ewo': AwesomeOscillatorIndicator(high=df['high'], low=df['low']).awesome_oscillator().iloc[-1]
            }
        except Exception as e:
            logger.error(f"Error computing TA indicators for {symbol}: {str(e)}")
            return {}


class TechnicalValidator(BaseTechnicalValidator):
    def __init__(self, client: FMPClient, throttle_seconds: int = 5, strict_mode: bool = True):
        super().__init__(client, throttle_seconds)
        self.strict_mode = strict_mode

    def evaluate(self, symbol_dict: dict) -> dict:
        symbol = self._get_symbol(symbol_dict)
        try:
            latest_20 = self._fetch_sma(symbol, 20)
            latest_50 = self._fetch_sma(symbol, 50)
            latest_200 = self._fetch_sma(symbol, 200)

            price = latest_20.get("close") if latest_20 else None
            sma20 = latest_20.get("sma") if latest_20 else None
            sma50 = latest_50.get("sma") if latest_50 else None
            sma200 = latest_200.get("sma") if latest_200 else None

            # If strict mode is on, enforce strict bullish checks
            if self.strict_mode:
                if not (price and sma20 and sma50 and sma200):
                    return {}
                if not (price > sma20 > sma50 > sma200):
                    return {}
            
            # Compute advanced TA volume/momentum indicators required by agent instructions
            ta_metrics = self._compute_ta_indicators(symbol)

            # Always attach whatever data we successfully pulled for debugging/agent context
            symbol_dict.update({
                'price': price, 
                'sma20': sma20, 
                'sma50': sma50, 
                'sma200': sma200,
                'technical_passed': bool(price and sma20 and sma50 and sma200 and price > sma20 > sma50 > sma200),
                **ta_metrics
            })
            return symbol_dict

        except Exception as e:
            logger.error(f"Error evaluating technicals for {symbol}: {str(e)}")
            return symbol_dict if not self.strict_mode else {}


class BearishTechnicalValidator(BaseTechnicalValidator):
    def evaluate(self, symbol_dict: dict) -> dict:
        """Validates bearish technicals: Price < SMA20 with supplementary SMA data"""
        symbol = self._get_symbol(symbol_dict)
        try:
            # 1. SMA 20
            latest_20 = self._fetch_sma(symbol, 20)
            if not latest_20:
                return {}
            
            price = latest_20.get("close")
            sma20 = latest_20.get("sma")
            
            # Condition: Price must be strictly below SMA20
            if price is None or sma20 is None or price >= sma20:
                return {}
            
            # 2. SMA 50
            latest_50 = self._fetch_sma(symbol, 50)
            if not latest_50:
                return {}
            sma50 = latest_50.get("sma")
            if sma50 is None:
                return {}

            # 3. SMA 200
            latest_200 = self._fetch_sma(symbol, 200)
            if not latest_200:
                return {}
            sma200 = latest_200.get("sma")
            if sma200 is None:
                return {}
                            
            ta_metrics = self._compute_ta_indicators(symbol)

            logger.info(f"📉 {symbol} passed bearish technical filters.")
            symbol_dict.update({
                'price': price, 
                'sma20': sma20, 
                'sma50': sma50, 
                'sma200': sma200,
                **ta_metrics
            })
            return symbol_dict

        except Exception as e:
            logger.error(f"Error evaluating bearish technicals for {symbol}: {str(e)}")
            return {}