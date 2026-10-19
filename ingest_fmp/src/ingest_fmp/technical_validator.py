import time
import logging
from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

class TechnicalValidator:
    def __init__(self, client: FMPClient, throttle_seconds: int = 5):
        self.client = client
        self.throttle_seconds = throttle_seconds

    def evaluate(self, symbol: str) -> bool:
        """
        Validates technical alignment with short-circuiting:
        Price > SMA20 > SMA50 > SMA200
        """
        try:
            # 1. SMA 20 (Shortest - fail fast)
            sma20_data = self.client.get_sma(symbol=symbol, period_length=20, timeframe="1day")
            time.sleep(self.throttle_seconds)
            if not sma20_data:
                return False
            
            latest_20 = sma20_data[0]
            price = latest_20.get("close")
            sma20 = latest_20.get("sma")
            if price is None or sma20 is None or price <= sma20:
                return False

            # 2. SMA 50
            sma50_data = self.client.get_sma(symbol=symbol, period_length=50, timeframe="1day")
            time.sleep(self.throttle_seconds)
            if not sma50_data:
                return False
            sma50 = sma50_data[0].get("sma")
            if sma50 is None or sma20 <= sma50:
                return False

            # 3. SMA 200
            sma200_data = self.client.get_sma(symbol=symbol, period_length=200, timeframe="1day")
            time.sleep(self.throttle_seconds)
            if not sma200_data:
                return False
            sma200 = sma200_data[0].get("sma")
            if sma200 is None or sma50 <= sma200:
                return False

            logger.info(f"✨ {symbol} passed technical filters.")
            return True

        except Exception as e:
            logger.error(f"Error evaluating technicals for {symbol}: {str(e)}")
            time.sleep(self.throttle_seconds)
            return False