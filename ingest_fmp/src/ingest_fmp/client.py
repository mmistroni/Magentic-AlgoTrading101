import time
import logging
import requests
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

class FMPClient:
    def __init__(self, api_key: Optional[str] = None, base_url: str = "https://financialmodelingprep.com/stable", min_delay_seconds: float = 2.0):
        import os
        self.api_key = api_key or os.environ.get("FMP_API_KEY")
        if not self.api_key:
            raise ValueError("FMP_API_KEY environment variable or explicit key must be provided.")
        
        self.base_url = base_url.rstrip("/")
        self.min_delay_seconds = min_delay_seconds
        self._last_request_time = 0.0

    def _throttle(self):
        """Ensures a minimum time gap between consecutive API requests."""
        elapsed = time.time() - self._last_request_time
        if elapsed < self.min_delay_seconds:
            sleep_time = self.min_delay_seconds - elapsed
            time.sleep(sleep_time)
        self._last_request_time = time.time()

    def _get(self, endpoint_path: str, params: Optional[Dict[str, Any]] = None) -> Any:
        """Internal helper handling requests, throttling, and error resilience."""
        self._throttle()
        
        url = f"{self.base_url}/{endpoint_path.lstrip('/')}"
        if params is None:
            params = {}
        params["apikey"] = self.api_key

        try:
            response = requests.get(url, params=params, timeout=30)
            
            if response.status_code == 429:
                logger.warning("FMP rate limit hit (429). Backing off for 60 seconds...")
                time.sleep(60)
                return self._get(endpoint_path, params) # Retry once after backoff
                
            response.raise_for_status()
            return response.json()
            
        except requests.exceptions.RequestException as e:
            logger.error(f"FMP API request failed for {url}: {str(e)}")
            return []

    # Specific Endpoint Wrappers (Using query parameter dictionary format)
    def get_company_screener(self, params: Dict[str, Any]) -> List[Dict[str, Any]]:
        return self._get("company-screener", params)

    def get_quote(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetches real-time stock quote including yearHigh, yearLow, and price via stable endpoint."""
        return self._get("quote", {"symbol": symbol})
    
    def get_financial_growth(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetches unified financial statement growth metrics via stable endpoint."""
        return self._get("financial-growth", {"symbol": symbol})
    
    def get_balance_sheet_growth(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetches balance sheet growth metrics via stable query parameter endpoint."""
        return self._get("balance-sheet-statement-growth", {"symbol": symbol})

    def get_cash_flow_growth(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetches cash flow statement growth metrics via stable query parameter endpoint."""
        return self._get("cash-flow-statement-growth", {"symbol": symbol})

    def get_key_metrics_ttm(self, symbol: str) -> List[Dict[str, Any]]:
        """Fetches key metrics TTM via stable query parameter endpoint."""
        return self._get("key-metrics-ttm", {"symbol": symbol})

    def get_institutional_ownership_summary(self, symbol: str) -> Dict[str, Any]:
        data = self._get("institutional-ownership/summary", {"symbol": symbol})
        return data[0] if isinstance(data, list) and data else {}

    def get_sma(self, symbol: str, period_length: int = 20, timeframe: str = "1day") -> List[Dict[str, Any]]:
        params = {
            "symbol": symbol,
            "periodLength": period_length,
            "timeframe": timeframe
        }
        return self._get("technical-indicators/sma", params)