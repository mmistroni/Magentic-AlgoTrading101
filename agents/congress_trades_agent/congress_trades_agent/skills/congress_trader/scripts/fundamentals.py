import os
import requests
from typing import Optional
from pydantic import BaseModel, Field
import os

def fetch_fmp_fundamentals(ticker: str) -> dict:
    """Fetches comprehensive valuation metrics and ratios from FMP and evaluates fundamental health."""
    api_key = os.getenv("FMP_API_KEY")
    if not api_key:
        return dict(
            ticker=ticker.upper(),
            error="FMP_API_KEY environment variable is missing."
        )

    metrics_list = _fetch_fmp_endpoint("key-metrics-ttm", ticker, api_key)
    ratios_list = _fetch_fmp_endpoint("ratios-ttm", ticker, api_key)
    quotes_list = _fetch_fmp_endpoint("quote", ticker, api_key)
    #

    if not metrics_list and not ratios_list and not quotes_list:
        return dict(
            ticker=ticker.upper(),
            error=f"No fundamental data and price data found across FMP endpoints for ticker {ticker}."
        )

    metrics = metrics_list[0] if isinstance(metrics_list, list) and metrics_list else {}
    ratios = ratios_list[0] if isinstance(ratios_list, list) and ratios_list else {}
    quotes = quotes_list[0] if isinstance(quotes_list, list) and quotes_list else {}

    pe_ratio = metrics.get("peRatioTTM") or metrics.get("peRatio")
    forward_pe = metrics.get("peRatioForwardTTM")
    fcf_yield = metrics.get("freeCashFlowYieldTTM")
    roe = metrics.get("roeTTM")
    price = quotes.get("price")
    debt_to_equity = ratios.get("debtToEquityRatioTTM") or ratios.get("debtToEquityTTM")

    verdict, health_score = _compute_valuation_verdict_and_score(pe_ratio, debt_to_equity)

    return dict(
        ticker=ticker.upper(),
        price = price,
        pe_ratio=pe_ratio,
        forward_pe=forward_pe,
        debt_to_equity=debt_to_equity,
        free_cash_flow_yield=fcf_yield,
        return_on_equity=roe,
        valuation_verdict=verdict,
        fundamental_health_score=health_score
    )

def _fetch_fmp_endpoint(endpoint: str, ticker: str, api_key: str) -> list | dict:
    """Internal helper to safely query FMP API endpoints."""
    url = f"https://financialmodelingprep.com/api/v3/{endpoint}/{ticker.upper()}?apikey={api_key}"
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            return response.json()
    except Exception as e:
        print(f"Error calling FMP endpoint {endpoint} for {ticker}: {e}")
    return []


def _compute_valuation_verdict_and_score(pe_ratio: Optional[float], debt_to_equity: Optional[float]) -> tuple[str, float]:
    """Applies basic quantitative guardrails to determine health score and valuation status."""
    score = 50.0
    verdict = "NEUTRAL"

    if pe_ratio is not None:
        if pe_ratio < 15:
            score += 20
            verdict = "UNDERVALUED"
        elif pe_ratio > 35:
            score -= 20
            verdict = "OVERVALUED"
        else:
            verdict = "FAIRLY_VALUED"

    if debt_to_equity is not None:
        if debt_to_equity < 1.0:
            score += 15
        elif debt_to_equity > 2.5:
            score -= 25

    return verdict, max(0.0, min(100.0, score))


