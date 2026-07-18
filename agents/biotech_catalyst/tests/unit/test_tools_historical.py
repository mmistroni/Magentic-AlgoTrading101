import pytest
from datetime import datetime, timedelta
from google.cloud import bigquery
import requests

import short_selling_agent.tools as tools
from short_selling_agent.tools import (
    get_bq_short_candidates,
    get_fmp_news,
    get_bearish_insider_sales,
    get_fmp_bigger_losers,
)

# --- Standardized Native Pytest Mocks ---
# --- Standardized Native Pytest Mocks ---
class DummyResponse:
    def __init__(self, json_data, status_code=200):
        self._json_data = json_data
        self.status_code = status_code  # 👈 Added status_code support
        
    def json(self):
        return self._json_data

    def raise_for_status(self):
        # 👈 Added to mimic requests behavior perfectly
        if self.status_code >= 400:
            raise requests.exceptions.HTTPError(f"Status {self.status_code}")
        return None

class DummyRow:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def items(self):
        return self.__dict__.items()
    def __iter__(self):
        return iter(self.__dict__.items())

class DummyJob:
    def __init__(self, rows): 
        self._rows = rows
    def result(self): 
        return self._rows

class DummyClient:
    _rows = []
    def __init__(self, project=None): pass
    def query(self, *args, **kwargs):
        return DummyJob(DummyClient._rows)


@pytest.fixture(autouse=True)
def fix_env(monkeypatch, mocker):
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("FMP_API_KEY", "DUMMY")
    # Globally mock telemetry infrastructure to avoid hitting live BigQuery tables
    mocker.patch("short_selling_agent.tools.log_news_context_to_bigquery")
    yield


# =============================================================================
# Tests for get_bq_short_candidates
# =============================================================================

def test_get_bq_short_candidates_historical(monkeypatch):
    # prepare fake rows for 2023-06-01
    DummyClient._rows = [
        DummyRow(ticker="AAA", price=10.0, change_pct=-5.0,
                 short_interest_pct=12.3, free_float=100000, is_squeeze_risk=False),
        DummyRow(ticker="BBB", price=20.0, change_pct=-3.2,
                 short_interest_pct=8.7, free_float=50000, is_squeeze_risk=True),
    ]
    monkeypatch.setattr(tools.bigquery, "Client", lambda project=None: DummyClient())
    out = get_bq_short_candidates(limit=2, as_of_date="2023-06-01")
    
    assert isinstance(out, list) and len(out) == 2
    assert out[0]["ticker"] == "AAA"
    assert out[1]["is_squeeze_risk"] is True


def test_get_bq_short_candidates_live(monkeypatch):
    # live mode: we don't patch Client, but we patch the table to return empty
    class EmptyClient(DummyClient):
        def query(self, *args, **kwargs):
            return DummyJob([])
            
    monkeypatch.setattr(tools.bigquery, "Client", lambda project=None: EmptyClient())
    out = get_bq_short_candidates(limit=1, as_of_date=None)
    assert out == []


# =============================================================================
# Tests for get_fmp_news (Historical & Live)
# =============================================================================

def test_get_fmp_news_historical(monkeypatch, mocker):
    mock_log_bq = mocker.patch("short_selling_agent.tools.log_news_context_to_bigquery")
    
    sample = [
        {"symbol": "ABC", "publishedDate": "2023-06-01", "title": "News A"},
        {"symbol": "XYZ", "publishedDate": "2023-06-01", "title": "Other News"},
        {"symbol": "ABC", "publishedDate": "2023-06-01", "title": "News B"},
    ]
    
    monkeypatch.setattr(requests, "get", lambda url, *args, **kwargs: DummyResponse(sample))

    rpt = get_fmp_news("ABC", as_of_date="2023-06-01")
    assert rpt.ticker == "ABC"
    assert rpt.error_message is None
    assert len(rpt.articles) == 2
    
    titles = [a.title for a in rpt.articles]
    assert "News A" in titles and "News B" in titles
    
    # Assert telemetry utility captures context when tracking elements are present
    mock_log_bq.assert_called_once()


def test_get_fmp_news_live(monkeypatch, mocker):
    mock_log_bq = mocker.patch("short_selling_agent.tools.log_news_context_to_bigquery")
    fake = [{"symbol": "XYZ", "publishedDate": "2026-04-29", "title": "Today’s Drop"}]
    
    monkeypatch.setattr(requests, "get", lambda url, *args, **kwargs: DummyResponse(fake))
    
    rpt = get_fmp_news("XYZ", as_of_date=None)
    assert rpt.error_message is None
    assert len(rpt.articles) == 1
    assert rpt.articles[0].title == "Today’s Drop"
    mock_log_bq.assert_called_once()


# =============================================================================
# Tests for get_bearish_insider_sales
# =============================================================================

def test_get_bearish_insider_sales_historical(monkeypatch):
    class TradeRow(dict):
        pass

    cutoff = datetime(2023, 6, 1) - timedelta(days=180)
    recent = (cutoff + timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")
    old = (cutoff - timedelta(days=1)).strftime("%Y-%m-%dT00:00:00.000Z")

    DummyClient._rows = [
        TradeRow(transactionDate=recent, transactionType="S-Sale",
                 securitiesTransacted=1000, price=5.0,
                 typeOfOwner="CEO", reportingName="Alice"),
        TradeRow(transactionDate=old, transactionType="S-Sale",
                 securitiesTransacted=100000, price=10.0,
                 typeOfOwner="CEO", reportingName="Bob"),
    ]
    monkeypatch.setattr(tools.bigquery, "Client", lambda project=None: DummyClient())

    rpt = get_bearish_insider_sales("AAA", days_back=180, min_value=1000, as_of_date="2023-06-01")
    
    assert rpt.total_dollars_dumped == pytest.approx(5000.0)
    assert len(rpt.significant_sales) == 1
    assert rpt.significant_sales[0].name == "Alice"


def test_get_bearish_insider_sales_live(monkeypatch):
    monkeypatch.setattr(requests, "get", lambda url, *args, **kwargs: DummyResponse([]))
    rpt = get_bearish_insider_sales("AAA", as_of_date=None)
    assert rpt.significant_sales == []
    assert rpt.total_dollars_dumped == 0.0


# =============================================================================
# Tests for get_fmp_bigger_losers (Historical with Fallback)
# =============================================================================

def test_get_fmp_bigger_losers_historical_bq_success(monkeypatch, mocker):
    """When BQ returns data for historical date, use it — skip fallback."""
    DummyClient._rows = [
        DummyRow(ticker="NVDA", price=800.0, change_pct=-0.15),
        DummyRow(ticker="TSLA", price=180.0, change_pct=-0.12),
    ]
    monkeypatch.setattr(tools.bigquery, "Client", lambda project=None: DummyClient())

    # Pure pytest patch setup to spy and isolate fallback execution
    mock_fallback = mocker.patch("short_selling_agent.tools._fetch_from_fmp_earning_drop_fallback", return_value=[])

    report = get_fmp_bigger_losers(limit=2, as_of_date="2023-06-01")

    assert len(report.losers) == 2
    assert report.losers[0].ticker == "NVDA"
    assert report.losers[0].change_pct == -0.15
    assert report.error_message is None
    mock_fallback.assert_not_called()


def test_get_bq_short_candidates_fallback_to_fmp_historical(monkeypatch, mocker):
    """When BQ returns no data for a historical date, it should fall back to FMP."""
    DummyClient._rows = []
    monkeypatch.setattr(tools.bigquery, "Client", lambda project: DummyClient(project))

    def fake_fallback(target_date: str, limit: int):
        assert target_date == "2023-10-25"
        assert limit == 5
        return [tools.MarketLoser(ticker="AMD", price=160.0, change_pct=-0.15)]

    mocker.patch("short_selling_agent.tools._fetch_from_fmp_earning_drop_fallback", side_effect=fake_fallback)

    result = get_bq_short_candidates(limit=5, as_of_date="2023-10-25")

    assert len(result) == 1
    assert result[0]["ticker"] == "AMD"
    assert result[0]["price"] == 160.0
    assert result[0]["change_pct"] == -0.15
    assert result[0]["short_interest_pct"] == 0.0
    assert result[0]["free_float"] == 0.0
    assert result[0]["is_squeeze_risk"] is False


def test_get_bq_short_candidates_fallback_to_fmp_live_mode(monkeypatch, mocker):
    """When as_of_date=None, it defaults to yesterday and falls back to FMP if BQ has no data."""
    expected_date = (datetime.now() - timedelta(days=1)).strftime("%Y-%m-%d")

    DummyClient._rows = []
    monkeypatch.setattr(tools.bigquery, "Client", lambda project: DummyClient(project))

    def fake_fallback(target_date: str, limit: int):
        assert target_date == expected_date
        assert limit == 5
        return [tools.MarketLoser(ticker="NVDA", price=800.0, change_pct=-0.18)]

    mocker.patch("short_selling_agent.tools._fetch_from_fmp_earning_drop_fallback", side_effect=fake_fallback)

    result = get_bq_short_candidates(limit=5, as_of_date=None)

    assert len(result) == 1
    assert result[0]["ticker"] == "NVDA"
    assert result[0]["price"] == 800.0
    assert result[0]["change_pct"] == -0.18
    assert result[0]["short_interest_pct"] == 0.0
    assert result[0]["free_float"] == 0.0
    assert result[0]["is_squeeze_risk"] is False