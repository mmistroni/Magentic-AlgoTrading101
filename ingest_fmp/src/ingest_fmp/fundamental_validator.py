import logging
from typing import Dict, Any, Optional
from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

class FundamentalValidator:
    def __init__(
        self, 
        client: FMPClient,
        min_eps_this_year: float = 0.20,
        min_eps_next_year: float = 0.20,
        min_eps_qtr: float = 0.20,
        min_sales_qtr: float = 0.20,
        min_roe: float = 0.20,
        min_gross_margin: float = 0.20,
        max_institutional_ownership: float = 0.60
    ):
        self.client = client
        self.min_eps_this_year = min_eps_this_year
        self.min_eps_next_year = min_eps_next_year
        self.min_eps_qtr = min_eps_qtr
        self.min_sales_qtr = min_sales_qtr
        self.min_roe = min_roe
        self.min_gross_margin = min_gross_margin
        self.max_institutional_ownership = max_institutional_ownership

    def evaluate(self, symbol: str) -> bool:
        """Validates fundamental criteria dynamically based on configured thresholds."""
        try:
            # 1. Growth metrics check
            growth_data = self.client.get_financial_growth(symbol)
            if not growth_data:
                return False
            
            latest_growth = growth_data[0]
            if (
                (latest_growth.get("epsgrowththisyear", 0) or 0) < self.min_eps_this_year or 
                (latest_growth.get("epsgrowthnextyear", 0) or 0) < self.min_eps_next_year or 
                (latest_growth.get("epsGrowthQuarterOverQuarter", 0) or 0) < self.min_eps_qtr or 
                (latest_growth.get("revenueGrowthQuarterOverQuarter", 0) or 0) < self.min_sales_qtr
            ):
                return False

            # 2. Profitability / Ratios check
            metrics_data = self.client.get_key_metrics_ttm(symbol)
            if not metrics_data:
                return False
            
            latest_metrics = metrics_data[0]
            if (
                (latest_metrics.get("returnOnEquityTTM", 0) or 0) < self.min_roe or 
                (latest_metrics.get("grossProfitMarginTTM", 0) or 0) < self.min_gross_margin
            ):
                return False

            # 3. Institutional Ownership check (if max limit is set)
            if self.max_institutional_ownership < 1.0:
                ownership_data = self.client.get_institutional_ownership_summary(symbol)
                inst_ownership_pct = ownership_data.get("institutionalOwnershipPercentage", 100) if ownership_data else 100
                if inst_ownership_pct >= self.max_institutional_ownership:
                    return False

            logger.info(f"✨ {symbol} passed fundamental filters for current strategy profile.")
            return True

        except Exception as e:
            logger.error(f"Error evaluating fundamentals for {symbol}: {str(e)}")
            return False