import logging
import pandas as pd
import time
from typing import List, Dict, Any
from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

class StockScreeners:
    def __init__(self, client: FMPClient):
        self.client = client

    def get_extra_watchlist(self) -> List[Dict[str, Any]]:
        """
        Fetches the extra watchlist using native FMP company-screener parameters:
        - Market Cap: > $2 Billion
        - Price: > $10
        - Average Volume: > 200K
        - Excludes ETFs and Funds
        - Actively trading US equities only
        """
        # Dictionary of native FMP screener query parameters based on your specification
        params: Dict[str, Any] = {
            "marketCapMoreThan": 2000000000,    # Mid cap over $2B
            "priceMoreThan": 10,               # Price over $10
            "avgVolumeMoreThan": 200000,       # Average volume over 200K
            "country": "US",                   # US markets
            "isEtf": "false",                  # Exclude ETFs
            "isFund": "false",                 # Exclude Funds
            "isActivelyTrading": "true",       # Only active tickers
            "limit": 1000                      # Pagination limit
        }

        logger.info("Fetching extra watchlist universe from FMP company-screener...")
        raw_data = self.client.get_company_screener(params)
        
        if not raw_data:
            logger.warning("No data returned from FMP screener for extra watchlist.")
            return []

        df = pd.DataFrame(raw_data)
        logger.info(f"Retrieved {len(df)} raw records from FMP screener.")

        # Optional secondary cleaning / filtering if needed via Pandas
        # e.g., dropping rows with missing symbols or zero prices
        if "symbol" in df.columns:
            df = df.dropna(subset=["symbol"])

        results = df.to_dict(orient="records")
        logger.info(f"Extra watchlist successfully processed with {len(results)} records.")
        return results

    def evaluate_technicals_with_throttling(self, symbols: list) -> list:
        """
        Iterates through shortlisted symbols, applies short-circuit SMA checks,
        and pauses between requests to respect FMP rate limits safely.
        """
        qualified_stocks = []
        
        for symbol in symbols:
            logger.info(f"Evaluating technicals for {symbol}...")
            try:
                # 1. Check SMA 20 (Shortest period - fail fast)
                sma20_data = self.client.get_sma(symbol=symbol, period_length=20, timeframe="1day")
                time.sleep(5) # Throttle
                
                if not sma20_data:
                    continue
                
                latest_20 = sma20_data[0]
                price = latest_20.get("close")
                sma20 = latest_20.get("sma")
                
                if price is None or sma20 is None or price <= sma20:
                    logger.debug(f"{symbol} failed Price > SMA20 check.")
                    continue

                # 2. Check SMA 50
                sma50_data = self.client.get_sma(symbol=symbol, period_length=50, timeframe="1day")
                time.sleep(5) # Throttle
                
                if not sma50_data:
                    continue
                sma50 = sma50_data[0].get("sma")
                
                if sma50 is None or sma20 <= sma50:
                    logger.debug(f"{symbol} failed SMA20 > SMA50 check.")
                    continue

                # 3. Check SMA 200
                sma200_data = self.client.get_sma(symbol=symbol, period_length=200, timeframe="1day")
                time.sleep(5) # Throttle
                
                if not sma200_data:
                    continue
                sma200 = sma200_data[0].get("sma")
                
                if sma200 is None or sma50 <= sma200:
                    logger.debug(f"{symbol} failed SMA50 > SMA200 check.")
                    continue

                # If it survives all checks, it qualifies!
                logger.info(f"✨ {symbol} passed all technical criteria!")
                qualified_stocks.append(symbol)

            except Exception as e:
                logger.error(f"Error processing technicals for {symbol}: {str(e)}")
                time.sleep(5) # Ensure sleep even on exception

        return qualified_stocks