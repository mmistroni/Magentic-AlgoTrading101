import logging
import pandas as pd
from typing import List, Dict, Any
from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

class StockScreeners:
    """
    Responsible solely for querying FMP company screener and 
    retrieving base descriptive stock universes.
    """
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
        params: Dict[str, Any] = {
            "marketCapMoreThan": 2000000000,
            "priceMoreThan": 10,
            "avgVolumeMoreThan": 200000,
            "country": "US",
            "isEtf": "false",
            "isFund": "false",
            "isActivelyTrading": "true",
            "limit": 1000
        }

        logger.info("Fetching extra watchlist universe from FMP company-screener...")
        raw_data = self.client.get_company_screener(params)
        
        if not raw_data:
            logger.warning("No data returned from FMP screener for extra watchlist.")
            return []

        df = pd.DataFrame(raw_data)
        logger.info(f"Retrieved {len(df)} raw records from FMP screener.")

        if "symbol" in df.columns:
            df = df.dropna(subset=["symbol"])

        results = df.to_dict(orient="records")
        logger.info(f"Extra watchlist successfully processed with {len(results)} records.")
        return results

    def get_custom_universe(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generic helper to fetch any custom descriptive universe from FMP screener
        based on strategy-specific parameters (e.g., Market Down, Swing, New Highs).
        """
        logger.info(f"Fetching custom screener universe with parameters: {params}")
        raw_data = self.client.get_company_screener(params)
        
        if not raw_data:
            logger.warning("No data returned for custom screener query.")
            return []

        df = pd.DataFrame(raw_data)
        if "symbol" in df.columns:
            df = df.dropna(subset=["symbol"])

        return df.to_dict(orient="records")