import logging
import pandas as pd
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