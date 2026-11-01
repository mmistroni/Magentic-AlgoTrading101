import logging
from typing import Dict, Any, Optional
from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

class BaseFundamentalValidator:
    """Base class providing shared helper methods and a standardized schema dictionary."""
    def __init__(self, client: FMPClient):
        self.client = client

    def _get_symbol(self, symbol_dict: dict) -> str:
        """Helper to safely retrieve the symbol/ticker from the dictionary."""
        return symbol_dict.get('symbol') or symbol_dict.get('ticker', '')

    def _get_standard_enrichment(
        self, 
        income_growth: dict = None, 
        bs_growth: dict = None, 
        cf_growth: dict = None,
        metrics_latest: dict = None, 
        inst_ownership_pct: float = None
    ) -> dict:
        """
        Maps stable statement growth endpoint keys (growth*-prefixed) to our 
        standardized BigQuery and Agent schema.
        """
        income_growth = income_growth or {}
        bs_growth = bs_growth or {}
        cf_growth = cf_growth or {}
        metrics_latest = metrics_latest or {}

        return {
            # Income Statement Growth
            "eps_growth": income_growth.get("growthEps") or income_growth.get("epsgrowth"),
            "revenue_growth": income_growth.get("growthRevenue") or income_growth.get("revenueGrowth"),
            "net_income_growth": income_growth.get("growthNetIncome") or income_growth.get("netIncomeGrowth"),
            
            # Balance Sheet Growth (Stable keys use growth* prefix)
            "asset_growth": bs_growth.get("growthTotalAssets"),
            "debt_growth": bs_growth.get("growthTotalDebt"),
            "book_value_growth": bs_growth.get("growthBookValuePerShare"),
            
            # Cash Flow Statement Growth
            "operating_cash_flow_growth": cf_growth.get("growthOperatingCashFlow") or cf_growth.get("growthNetCashProvidedByOperatingActivites"),
            "free_cash_flow_growth": cf_growth.get("growthFreeCashFlow"),
            
            # Profitability & Ownership TTM Ratios
            "return_on_equity": metrics_latest.get("returnOnEquityTTM"),
            "gross_margin": metrics_latest.get("grossProfitMarginTTM"),
            "institutional_ownership_pct": inst_ownership_pct
        }

class FundamentalValidator(BaseFundamentalValidator):
    def __init__(
        self, 
        client: FMPClient,
        min_eps_growth: float = 0.0,
        min_roe: float = 0.0,
        min_gross_margin: float = 0.0,
        max_institutional_ownership: float = 0.60
    ):
        super().__init__(client)
        self.min_eps_growth = min_eps_growth
        self.min_roe = min_roe
        self.min_gross_margin = min_gross_margin
        self.max_institutional_ownership = max_institutional_ownership

    def evaluate(self, symbol_dict: dict) -> dict:
        symbol = self._get_symbol(symbol_dict)
        try:
            # 1. Fetch financial growth data
            growth_data = self.client.get_financial_growth(symbol)
            if not growth_data:
                return {}
            
            latest_growth = growth_data[0]
            eps_growth = latest_growth.get("epsgrowth", 0) or 0
            if eps_growth < self.min_eps_growth:
                return {}

            # 2. Profitability / Ratios check
            metrics_data = self.client.get_key_metrics_ttm(symbol)
            if not metrics_data:
                return {}
            
            latest_metrics = metrics_data[0]
            roe = latest_metrics.get("returnOnEquityTTM", 0) or 0
            gross_margin = latest_metrics.get("grossProfitMarginTTM", 0) or 0

            if roe < self.min_roe or gross_margin < self.min_gross_margin:
                return {}

            # 3. Institutional Ownership check
            inst_ownership_pct = 100.0
            if self.max_institutional_ownership < 1.0:
                ownership_data = self.client.get_institutional_ownership_summary(symbol)
                inst_ownership_pct = ownership_data.get("institutionalOwnershipPercentage", 100) if ownership_data else 100
                if inst_ownership_pct >= self.max_institutional_ownership:
                    return {}

            logger.info(f"✨ {symbol} passed fundamental filters with unified financial-growth enrichment.")
            
            symbol_dict.update(self._get_standard_enrichment(latest_growth, latest_metrics, inst_ownership_pct))
            return symbol_dict

        except Exception as e:
            logger.error(f"Error evaluating fundamentals for {symbol}: {str(e)}")
            return {}


class MarketDownFundamentalValidator(BaseFundamentalValidator):
    def evaluate(self, symbol_dict: dict) -> dict:
        symbol = self._get_symbol(symbol_dict)
        try:
            growth_data = self.client.get_financial_growth(symbol)
            if not growth_data:
                return {}
            
            latest_growth = growth_data[0]
            eps_growth = latest_growth.get("epsgrowth")

            if eps_growth is None or eps_growth >= 0.0:
                logger.debug(f"{symbol} failed negative EPS growth check (epsgrowth: {eps_growth})")
                return {}

            metrics_data = self.client.get_key_metrics_ttm(symbol)
            latest_metrics = metrics_data[0] if metrics_data else {}

            logger.info(f"✨ {symbol} passed Market Down fundamental filter (Negative EPS growth).")
            
            symbol_dict.update(self._get_standard_enrichment(latest_growth, latest_metrics, inst_ownership_pct=None))
            return symbol_dict

        except Exception as e:
            logger.error(f"Error evaluating Market Down fundamentals for {symbol}: {str(e)}")
            return {}