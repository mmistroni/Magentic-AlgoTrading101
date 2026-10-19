import os
import logging
import requests
from typing import Optional, Dict, Any, List

logger = logging.getLogger(__name__)

class FMPClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://financialmodelingprep.com/stable"):
        self.api_key = api_key or os.environ.get("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY environment variable or explicit key must be provided.")
        self.base_url = base_url

    def get_company_screener(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Fetch filtered stock lists from FMP Company Screener API."""
        endpoint = f"{self.base_url}/company-screener"
        query_params = params.copy()
        query_params["apikey"] = self.api_key

        try:
            response = requests.get(endpoint, params=query_params, timeout=30)
            response.raise_for_status()
            data = response.json()
            if isinstance(data, list):
                return data
            logger.warning(f"Unexpected response format from FMP screener: {type(data)}")
            return []
        except requests.exceptions.RequestException as e:
            logger.error(f"FMP API request failed: {str(e)}")
            return []