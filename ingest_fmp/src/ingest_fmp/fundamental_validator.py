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
        growth_latest: dict = None, 
        metrics_latest: dict = None, 
        inst_ownership_pct: float = None
    ) -> dict:
        """
        Returns a standardized dictionary of fundamental metrics 
        to ensure uniform BigQuery schema output across all strategies.
        """
        growth_latest = growth_latest or {}
        metrics_latest = metrics_latest or {}

        return {
            "eps_growth_this_year": growth_latest.get("epsgrowththisyear"),
            "eps_growth_next_year": growth_latest.get("epsgrowthnextyear"),
            "eps_growth_qtr": growth_latest.get("epsGrowthQuarterOverQuarter"),
            "revenue_growth_qtr": growth_latest.get("revenueGrowthQuarterOverQuarter"),
            "return_on_equity": metrics_latest.get("returnOnEquityTTM"),
            "gross_margin": metrics_latest.get("grossProfitMarginTTM"),
            "institutional_ownership_pct": inst_ownership_pct
        }


class FundamentalValidator(BaseFundamentalValidator):
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
        super().__init__(client)
        self.min_eps_this_year = min_eps_this_year
        self.min_eps_next_year = min_eps_next_year
        self.min_eps_qtr = min_eps_qtr
        self.min_sales_qtr = min_sales_qtr
        self.min_roe = min_roe
        self.min_gross_margin = min_gross_margin
        self.max_institutional_ownership = max_institutional_ownership

    def evaluate(self, symbol_dict: dict) -> dict:
        symbol = self._get_symbol(symbol_dict)
        try:
            # 1. Growth metrics check
            growth_data = self.client.get_financial_growth(symbol)
            if not growth_data:
                return {}
            
            latest_growth = growth_data[0]
            eps_this_year = latest_growth.get("epsgrowththisyear", 0) or 0
            eps_next_year = latest_growth.get("epsgrowthnextyear", 0) or 0
            eps_qtr = latest_growth.get("epsGrowthQuarterOverQuarter", 0) or 0
            sales_qtr = latest_growth.get("revenueGrowthQuarterOverQuarter", 0) or 0

            if (
                eps_this_year < self.min_eps_this_year or 
                eps_next_year < self.min_eps_next_year or 
                eps_qtr < self.min_eps_qtr or 
                sales_qtr < self.min_sales_qtr
            ):
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

            logger.info(f"✨ {symbol} passed fundamental filters for current strategy profile.")
            
            # Update dictionary with standardized keys
            symbol_dict.update(self._get_standard_enrichment(latest_growth, latest_metrics, inst_ownership_pct))
            return symbol_dict

        except Exception as e:
            logger.error(f"Error evaluating fundamentals for {symbol}: {str(e)}")
            return {}


class MarketDownFundamentalValidator(BaseFundamentalValidator):
    def evaluate(self, symbol_dict: dict) -> dict:
        """
        Validates Market Down criteria (Negative EPS growth next year),
        while still populating the full standardized fundamental schema keys.
        """
        symbol = self._get_symbol(symbol_dict)
        try:
            growth_data = self.client.get_financial_growth(symbol)
            if not growth_data:
                return {}
            
            latest_growth = growth_data[0]
            eps_next_year = latest_growth.get("epsgrowthnextyear")

            # Condition: EPS growth next year must be strictly negative (< 0.0)
            if eps_next_year is None or eps_next_year >= 0.0:
                logger.debug(f"{symbol} failed negative EPS growth check (epsgrowthnextyear: {eps_next_year})")
                return {}

            # Optionally fetch metrics too so the schema remains 100% identical
            metrics_data = self.client.get_key_metrics_ttm(symbol)
            latest_metrics = metrics_data[0] if metrics_data else {}

            logger.info(f"✨ {symbol} passed Market Down fundamental filter (Negative EPS growth).")
            
            # Update dictionary with the EXACT SAME standardized keys
            symbol_dict.update(self._get_standard_enrichment(latest_growth, latest_metrics, inst_ownership_pct=None))
            return symbol_dict

        except Exception as e:
            logger.error(f"Error evaluating Market Down fundamentals for {symbol}: {str(e)}")
            return {}