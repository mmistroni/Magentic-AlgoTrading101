import os
import json
from datetime import datetime, timedelta
import pytest
import requests

import short_selling_agent.tools as tools
from short_selling_agent.tools import (
    get_fmp_bigger_losers,
    get_fmp_news,
    get_bearish_insider_sales,
    get_squeeze_metrics,
    get_bq_short_candidates
)
from short_selling_agent.stage_tools import get_plus500_universe


#------------------------------------------------------------------------------
# Fixture to set/clear env vars
#------------------------------------------------------------------------------
@pytest.fixture(autouse=True)
def fix_env(monkeypatch):
    # ensure API key is present
    monkeypatch.setenv("FMP_API_KEY", "DUMMYKEY")
    monkeypatch.setenv("GCP_PROJECT_ID", "my-project")
    yield
    # no teardown needed


#------------------------------------------------------------------------------
# Helpers
#------------------------------------------------------------------------------
class DummyResponse:
    def __init__(self, payload=None, exc=None, status_code=200):
        self._payload = payload
        self._exc = exc
        self.status_code = status_code  # Required by .status_code checks

    def json(self):
        if self._exc:
            raise self._exc
        return self._payload

class DummyRow:
    def __init__(self, **kwargs):
        for k, v in kwargs.items():
            setattr(self, k, v)


class DummyJob:
    def __init__(self, rows):
        self._rows = rows

    def result(self):
        return self._rows


class DummyClient:
    def __init__(self, project=None):
        self.project = project

    def query(self, query, job_config=None):
        # return what the test has injected into DummyClient._rows
        return DummyJob(DummyClient._rows)

#------------------------------------------------------------------------------
# Tests for get_fmp_bigger_losers
#------------------------------------------------------------------------------
# -----------------------------------------------------------------------------
# Tests for get_fmp_bigger_losers
# -----------------------------------------------------------------------------
def test_get_fmp_bigger_losers_success(monkeypatch):
    sample = [
        {"symbol": "AAPL", "price": 150.0, "changesPercentage": -2.3},
        {"symbol": "TSLA", "price": 600.0, "changesPercentage": -5.0},
    ]

    def mock_get(url, *args, **kwargs):
        return DummyResponse(sample, status_code=200)  # ✅ Now has status_code

    monkeypatch.setattr(requests, "get", mock_get)
    report = get_fmp_bigger_losers()
    assert report.error_message is None
    assert len(report.losers) == 2
    assert report.losers[0].ticker == "AAPL"
    assert pytest.approx(report.losers[0].change_pct) == -0.023


#------------------------------------------------------------------------------
# Tests for get_fmp_news
#------------------------------------------------------------------------------
def test_get_fmp_news_no_data(monkeypatch, mocker):
    # 1. 🛡️ PATCH: Spy on the BigQuery logging method using the mocker fixture
    mock_log_bq = mocker.patch("short_selling_agent.tools.log_news_context_to_bigquery")
    monkeypatch.setattr(requests, "get", lambda url, *args, **kwargs: DummyResponse([]))
    resp = get_fmp_news("XYZ")
    assert resp.ticker == "XYZ"
    assert resp.articles == []
    assert "no news found" in resp.error_message.lower()
    mock_log_bq.assert_not_called()

def test_get_fmp_news_success(monkeypatch, mocker):
    # 1. 🛡️ PATCH: Spy on the BigQuery logging method using the mocker fixture
    mock_log_bq = mocker.patch("short_selling_agent.tools.log_news_context_to_bigquery")
    payload = [
        {"symbol": "ABC", "publishedDate": "2026-04-28", "title": "Big Drop!"},
        {"symbol": "ABC", "publishedDate": "2026-04-27", "title": "Earnings Miss"},
        {"symbol": "XYZ", "publishedDate": "2026-04-27", "title": "Ignore this"},
    ]
    # 🛠️ Change this lambda signature here as well
    monkeypatch.setattr(requests, "get", lambda url, *args, **kwargs: DummyResponse(payload))

    resp = get_fmp_news("ABC")
    assert resp.ticker == "ABC"
    
    # It should find exactly the 2 ABC articles and ignore XYZ
    assert len(resp.articles) == 2
    assert resp.error_message is None
    assert resp.articles[0].title == "Big Drop!"

    # 5. ✅ ASSERTION: Logging MUST be triggered since valid articles were compiled
    mock_log_bq.assert_called_once()
    
    # 6. Deep inspection of the tracking parameters passed to your logging tool layer
    called_args, called_kwargs = mock_log_bq.call_args
    assert called_args[0] == "ABC"            # Validating ticker positional argument match
    assert isinstance(called_args[2], list)    # Validating that data chunk payload is an extracted list
    assert len(called_args[2]) == 2




#------------------------------------------------------------------------------
# Tests for get_bearish_insider_sales
#------------------------------------------------------------------------------
def make_trade(date, tx_type, shares, price, owner, name="John Doe"):
    return {
        "transactionDate": date,
        "transactionType": tx_type,
        "securitiesTransacted": shares,
        "price": price,
        "typeOfOwner": owner,
        "reportingName": name,
    }

def test_get_bearish_insider_sales_filters(monkeypatch):
    today = datetime.now().strftime("%Y-%m-%d")
    old_date = (datetime.now() - timedelta(days=200)).strftime("%Y-%m-%d")
    data = [
        # valid CEO sale
        make_trade(today, "S-Sale", 10000, 50.0, "CEO"),
        # wrong type
        make_trade(today, "S-Buy", 10000, 50.0, "CEO"),
        # too old
        make_trade(old_date, "S-Sale", 10000, 50.0, "CEO"),
        # below min_value
        make_trade(today, "S-Sale", 1, 1.0, "CEO"),
        # non-target role
        make_trade(today, "S-Sale", 10000, 50.0, "CUSTODIAN"),
    ]
    monkeypatch.setenv("FMP_API_KEY", "DUMMY")
    monkeypatch.setattr(requests, "get", lambda url: DummyResponse(data))
    report = get_bearish_insider_sales("XYZ", days_back=180, min_value=100.0)
    # only the first trade should count: 10000 * 50.0 = 500k
    assert report.total_dollars_dumped == 500000.0
    assert len(report.significant_sales) == 1
    assert report.significant_sales[0].title == "CEO"

def test_get_bearish_insider_sales_exception(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url: DummyResponse(exc=RuntimeError("fail")))
    report = get_bearish_insider_sales("XYZ")
    assert report.total_dollars_dumped == 0.0
    assert report.significant_sales == []
    assert "fail" in report.error_message.lower()


#------------------------------------------------------------------------------
# Tests for get_squeeze_metrics
#------------------------------------------------------------------------------
def test_get_squeeze_metrics_success(monkeypatch):
    def fake_get(url):
        if "stock-short-interest" in url:
            return DummyResponse([{"shortPercentOfFloat": 12.34}])
        if "shares_float" in url:
            return DummyResponse([{"freeFloat": 876543.0}])
        return DummyResponse([])
    monkeypatch.setattr(requests, "get", fake_get)
    short_pct, free_float = get_squeeze_metrics("ABC")
    assert short_pct == pytest.approx(12.34)
    assert free_float == pytest.approx(876543.0)

def test_get_squeeze_metrics_missing(monkeypatch):
    # missing fields => defaults
    def fake_get2(url):
        if "stock-short-interest" in url:
            return DummyResponse([{"shortPercentOfFloat": None}])
        if "shares_float" in url:
            return DummyResponse([{"freeFloat": None}])
        return DummyResponse([])
    monkeypatch.setattr(requests, "get", fake_get2)
    sp, ff = get_squeeze_metrics("ABC")
    assert sp == 0.0
    assert ff == tools._FLOAT_DEFAULT if hasattr(tools, "_FLOAT_DEFAULT") else 999999999.0

def test_get_squeeze_metrics_exception(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url: (_ for _ in ()).throw(Exception("boom")))
    sp, ff = get_squeeze_metrics("XYZ")
    assert sp == 0.0
    assert ff == 999999999.0


#------------------------------------------------------------------------------
# Tests for get_bq_short_candidates
#------------------------------------------------------------------------------
def test_bq_short_candidates_live_mode_uses_yesterday(monkeypatch):
    """
    When as_of_date=None, get_bq_short_candidates:
      - Defaults to yesterday
      - BQ returns nothing
      - Falls back to _fetch_from_fmp_earning_drop_fallback
      - Returns fallback data in dict format
    """
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    # -------------------------------
    # 🧱 Step 1: Mock BQ → return empty
    # -------------------------------
    DummyClient._rows = []
    monkeypatch.setattr(tools.bigquery, "Client", lambda project: DummyClient(project))

    # -------------------------------
    # 🔁 Step 2: Mock fallback → return list of MarketLoser
    # Use plain function to avoid Mock()
    # -------------------------------
    def fake_fallback(date_str, limit):
        assert limit == 5
        loser = tools.MarketLoser(ticker="NVDA", price=800.0, change_pct=-0.18)
        return [loser]

    monkeypatch.setattr(tools, "_fetch_from_fmp_earning_drop_fallback", fake_fallback)

    # -------------------------------
    # 🧪 Step 3: Run
    # -------------------------------
    result = get_bq_short_candidates(limit=5, as_of_date=None)

    # -------------------------------
    # ✅ Assert
    # -------------------------------
    assert len(result) == 1
    assert result[0]["ticker"] == "NVDA"
    assert result[0]["price"] == 800.0
    assert result[0]["change_pct"] == -0.18
    assert result[0]["short_interest_pct"] == 0.0
    assert result[0]["free_float"] == 0.0
    assert result[0]["is_squeeze_risk"] is False


#------------------------------------------------------------------------------
# Tests for get_plus500_universe
#------------------------------------------------------------------------------
def test_get_plus500_universe_success(monkeypatch):
    rows = [DummyRow(ticker="aaa"), DummyRow(ticker="BbB "), DummyRow(ticker=None)]
    DummyClient._rows = rows
    monkeypatch.setattr(tools.bigquery, "Client", lambda project=None: DummyClient(project))
    report = get_plus500_universe()
    assert "AAA" in report.tickers
    assert "BBB" in report.tickers
    assert report.error_message is None

def test_get_plus500_universe_failure(monkeypatch):
    def bad_client(*args, **kwargs):
        raise RuntimeError("BQ gone")
    monkeypatch.setattr(tools.bigquery, "Client", bad_client)
    report = get_plus500_universe()
    assert report.tickers == []
    assert "BQ gone" in report.error_message

def test_get_fmp_news_live(monkeypatch):
    """
    Live mode: calls FMP stock news API with no date filters.
    Uses existing DummyResponse to handle exceptions correctly.
    """
    fake = [{"symbol": "XYZ", "publishedDate": "2026-04-29", "title": "Today’s Drop"}]

    def mock_get(url, *args, **kwargs):
        return DummyResponse(fake)

    monkeypatch.setattr(requests, "get", mock_get)
    rpt = get_fmp_news("XYZ", as_of_date=None)
    assert rpt.error_message is None
    assert len(rpt.articles) == 1
    assert rpt.articles[0].title == "Today’s Drop"