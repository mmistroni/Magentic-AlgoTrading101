import pytest
from datetime import datetime, timedelta
from google.cloud import bigquery
import requests

import short_selling_agent.tools as tools
from short_selling_agent.tools import (
    get_bq_short_candidates,
    get_fmp_news,
    get_bearish_insider_sales,
)

# Dummy BigQuery support
class DummyRow:
    def __init__(self, **kwargs):
        self.__dict__.update(kwargs)
    def items(self):
        return self.__dict__.items()
    def __iter__(self):
        return iter(self.__dict__.items())

class DummyJob:
    def __init__(self, rows): self._rows = rows
    def result(self): return self._rows

class DummyClient:
    _rows = []
    def __init__(self, project=None): pass
    def query(self, *args, **kwargs):
        return DummyJob(DummyClient._rows)

@pytest.fixture(autouse=True)
def fix_env(monkeypatch):
    monkeypatch.setenv("GCP_PROJECT_ID", "test-project")
    monkeypatch.setenv("FMP_API_KEY", "DUMMY")
    yield

# ---------------------------------------------------------------------
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
    # we get list of dicts
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


# ---------------------------------------------------------------------
def test_get_fmp_news_historical(monkeypatch):
    # fake two rows from historical table
    class NewsRow:
        def __init__(self, publishedDate, title):
            self.publishedDate = publishedDate
            self.title = title

    monkeypatch.setattr(tools.bigquery, "Client", lambda project=None: DummyClient())
    DummyClient._rows = [
        NewsRow(publishedDate=datetime(2023,6,1,9,0,0), title="News A"),
        NewsRow(publishedDate=datetime(2023,6,1,8,0,0), title="News B"),
    ]

    rpt = get_fmp_news("ABC", as_of_date="2023-06-01")
    assert rpt.ticker == "ABC"
    assert len(rpt.articles) == 2
    assert rpt.articles[0].title == "News A"

def test_get_fmp_news_live(monkeypatch):
    # patch requests.get for live path
    fake = [{"publishedDate":"2026-04-29","title":"Today’s Drop"}]
    monkeypatch.setattr(requests, "get", lambda url: type("R",(object,),{"json":lambda self: fake})())
    rpt = get_fmp_news("XYZ", as_of_date=None)
    assert rpt.error_message is None
    assert rpt.articles[0].title == "Today’s Drop"


# ---------------------------------------------------------------------
def test_get_bearish_insider_sales_historical(monkeypatch):
    # two trades: one CEO S-Sale within window, one too old
    class TradeRow(dict):
        pass

    cutoff = datetime(2023,6,1) - timedelta(days=180)
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

    rpt = get_bearish_insider_sales("AAA",
        days_back=180, min_value=1000, as_of_date="2023-06-01"
    )
    # Only the recent CEO sale counts: 1,000*5=5,000 > 1,000
    assert rpt.total_dollars_dumped == pytest.approx(5000.0)
    assert len(rpt.significant_sales) == 1
    assert rpt.significant_sales[0].name == "Alice"

def test_get_bearish_insider_sales_live(monkeypatch):
    # live path: patch requests.get to return empty list
    monkeypatch.setattr(requests, "get", lambda url: type("R",(object,),{"json":lambda self: []})())
    rpt = get_bearish_insider_sales("AAA", as_of_date=None)
    assert rpt.significant_sales == []
    assert rpt.total_dollars_dumped == 0.0