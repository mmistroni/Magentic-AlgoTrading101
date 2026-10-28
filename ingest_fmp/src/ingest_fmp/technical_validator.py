import time
import logging
from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

class BaseTechnicalValidator:
    """Base class to share common SMA fetching and throttling logic."""
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


class TechnicalValidator(BaseTechnicalValidator):
    def evaluate(self, symbol_dict: dict) -> dict:
        """
        Validates bullish technical alignment with short-circuiting:
        Price > SMA20 > SMA50 > SMA200
        """
        symbol = self._get_symbol(symbol_dict)
        try:
            # 1. SMA 20 (Shortest - fail fast)
            latest_20 = self._fetch_sma(symbol, 20)
            if not latest_20:
                return {}
            
            price = latest_20.get("close")
            sma20 = latest_20.get("sma")
            if price is None or sma20 is None or price <= sma20:
                return {}

            # 2. SMA 50
            latest_50 = self._fetch_sma(symbol, 50)
            if not latest_50:
                return {}
            sma50 = latest_50.get("sma")
            if sma50 is None or sma20 <= sma50:
                return {}

            # 3. SMA 200
            latest_200 = self._fetch_sma(symbol, 200)
            if not latest_200:
                return {}
            sma200 = latest_200.get("sma")
            if sma200 is None or sma50 <= sma200:
                return {}

            logger.info(f"✨ {symbol} passed technical filters.")
            symbol_dict.update({'price': price, 'sma20': sma20, 'sma50': sma50, 'sma200': sma200})
            return symbol_dict

        except Exception as e:
            logger.error(f"Error evaluating technicals for {symbol}: {str(e)}")
            return {}


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
                            
            logger.info(f"📉 {symbol} passed bearish technical filters.")
            symbol_dict.update({
                'price': price, 
                'sma20': sma20, 
                'sma50': sma50, 
                'sma200': sma200
            })
            return symbol_dict

        except Exception as e:
            logger.error(f"Error evaluating bearish technicals for {symbol}: {str(e)}")
            return {}