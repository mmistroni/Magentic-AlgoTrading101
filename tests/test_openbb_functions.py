import pytest
from openbb_functions import get_ticker_from_query, get_company_overview, get_stock_price


def test_get_ticker_from_query():
    qry = 'What is the company profile  for COLM'
    assert 'COLM' == get_ticker_from_query(qry)

def test_get_stock_price():
    qry = 'What is the latest stock price for XOM'
    res = get_stock_price(qry)

    print(res)

    assert res


def test_get_company_overview():
    qry = 'What is the company profile  for COLM'
    res  =get_company_overview(qry)
    print (res)


    assert res is not None
    assert len(res) > 0

