import pytest
from openbb_functions import get_ticker_from_query, get_company_overview


def test_get_ticker_from_query():
    qry = 'What is the company profile  for COLM'
    assert 'COLM' == get_ticker_from_query(qry)

def test_get_company_overview():
    qry = 'What is the company profile  for COLM'
    res  =get_company_overview(qry)
    assert res is not None
    assert len(res) > 0

