import time
import logging
from typing import Dict, Any
from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

class FundamentalValidator:
    def __init__(self, client: FMPClient, throttle_seconds: int = 3):
        self.client = client
        self.throttle_seconds = throttle_seconds

    def evaluate(self, symbol: str) -> bool:
        """
        Validates fundamental criteria:
        - EPS Growth This/Next Year > 20%
        - EPS & Sales Growth Qtr over Qtr > 20%
        - Gross Margin > 20%
        - Return on Equity > 20%
        - Institutional Ownership < 60%
        """
        try:
            # 1. Growth metrics check
            growth_data = self.client.get_financial_growth(symbol)
            time.sleep(self.throttle_seconds)
            if not growth_data:
                return False
            
            latest_growth = growth_data[0]
            if (
                (latest_growth.get("epsgrowththisyear", 0) or 0) < 0.20 or 
                (latest_growth.get("epsgrowthnextyear", 0) or 0) < 0.20 or 
                (latest_growth.get("epsGrowthQuarterOverQuarter", 0) or 0) < 0.20 or 
                (latest_growth.get("revenueGrowthQuarterOverQuarter", 0) or 0) < 0.20
            ):
                return False

            # 2. Profitability / Ratios check
            metrics_data = self.client.get_key_metrics_ttm(symbol)
            time.sleep(self.throttle_seconds)
            if not metrics_data:
                return False
            
            latest_metrics = metrics_data[0]
            if (
                (latest_metrics.get("returnOnEquityTTM", 0) or 0) < 0.20 or 
                (latest_metrics.get("grossProfitMarginTTM", 0) or 0) < 0.20
            ):
                return False

            # 3. Institutional Ownership check
            ownership_data = self.client.get_institutional_ownership_summary(symbol)
            time.sleep(self.throttle_seconds)
            
            inst_ownership_pct = ownership_data.get("institutionalOwnershipPercentage", 100) if ownership_data else 100
            if inst_ownership_pct >= 0.60:
                return False

            logger.info(f"✨ {symbol} passed fundamental filters.")
            return True

        except Exception as e:
            logger.error(f"Error evaluating fundamentals for {symbol}: {str(e)}")
            time.sleep(self.throttle_seconds)
            return False