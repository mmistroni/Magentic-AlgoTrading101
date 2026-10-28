import logging
import pandas as pd
from typing import List, Dict, Any
from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

class StockScreeners:
    """
    Unified screener class responsible for fetching and cleaning 
    descriptive stock universes from FMP based on dynamic parameter dictionaries.
    """
    def __init__(self, client: FMPClient):
        self.client = client

    def get_screeners(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        Generic, parameterized method to fetch any descriptive universe from FMP
        company screener endpoint.
        """
        logger.info(f"Fetching FMP company screener with parameters: {params}")
        raw_data = self.client.get_company_screener(params)
        
        if not raw_data:
            logger.warning("No data returned from FMP screener for the given parameters.")
            return []

        df = pd.DataFrame(raw_data)
        logger.info(f"Retrieved {len(df)} raw records from FMP screener.")

        # Clean up records missing vital symbols
        if "symbol" in df.columns:
            df = df.dropna(subset=["symbol"])

        results = df.to_dict(orient="records")
        logger.info(f"Screener successfully processed {len(results)} candidate records.")
        return results