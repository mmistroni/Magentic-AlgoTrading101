import pytest

from short_selling_agent.fmp_tools import get_all_data_for_ticker 

def test_fmp_calls():
    ticker = 'AAPL'
    data = get_all_data_for_ticker(ticker)
    assert isinstance(data, dict)
    assert 'shortDate' in data
    assert 'shortInterest' in data
    assert 'shortPercent' in data
    assert 'historicalEarnings' in data
    assert 'companyProfile' in data