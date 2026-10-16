import os
from unittest.mock import patch
import pytest

from congress_trades_agent.skills.congress_trader.scripts.fundamentals import \
    fetch_fmp_fundamentals


@patch("congress_trades_agent.skills.congress_trader.scripts.fundamentals.requests.get")
def test_fetch_fmp_fundamentals_success(mock_get, monkeypatch):
    monkeypatch.setenv("FMP_API_KEY", "fake_key")
    
    # Mock responses for key-metrics-ttm and ratios-ttm
    class MockResponse:
        def __init__(self, json_data, status_code):
            self.json_data = json_data
            self.status_code = status_code
        def json(self):
            return self.json_data

    # Side effect to handle multiple calls to different endpoints
    def side_effect(url, timeout=10):
        if "key-metrics-ttm" in url:
            return MockResponse([{"peRatioTTM": 12.5, "freeCashFlowYieldTTM": 0.08}], 200)
        elif "ratios-ttm" in url:
            return MockResponse([{"debtToEquityRatioTTM": 0.5}], 200)
        return MockResponse([], 404)

    mock_get.side_effect = side_effect

    result = fetch_fmp_fundamentals("AAPL")
    
    assert result["ticker"] == "AAPL"
    assert result["pe_ratio"] == 12.5
    assert result["debt_to_equity"] == 0.5
    assert result["valuation_verdict"] == "UNDERVALUED"
    assert result["fundamental_health_score"] > 50.0
    assert result.get("error") is None

def test_fetch_fmp_fundamentals_missing_key(monkeypatch):
    monkeypatch.delenv("FMP_API_KEY", raising=False)
    result = fetch_fmp_fundamentals("AAPL")
    assert result["error"] == "FMP_API_KEY environment variable is missing."