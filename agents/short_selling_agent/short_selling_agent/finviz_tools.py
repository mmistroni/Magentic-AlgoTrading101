## finviz utilities
#https://pypi.org/project/finvizfinance/
# https://finvizfinance.readthedocs.io/en/latest/
#https://medium.com/the-investors-handbook/the-best-finviz-screens-for-growth-investors-72795f507b91

#https://www.justetf.com/uk/etf-profile.html?isin=IE000NDWFGA5
#https://www.justetf.com/uk/etf-profile.html?isin=IE000M7V94E1#chart URANIUM ETF
from finvizfinance.screener.overview import Overview
import numpy as np
import logging
from datetime import date
import requests
import asyncio



def _run_screener(filters):
    from numpy import nan
    foverview = Overview()
    foverview.set_filter(filters_dict=filters)
    df = foverview.screener_view()
    if df is not None and df.shape[0] > 0:
        return df.convert_dtypes().replace({nan: None}).to_dict(orient="records")
    return []
    #return df.to_dict('records') if df is not None else []

def get_short_sell_filter():

    filters_dict = {'Market Cap.':'+Small (over $300mln)',
                    'Average Volume' : 'Over 500K',
                    'EPS growthnext 5 years' :  'Negative (<0%)',
                    '200-Day Simple Moving Average': 'Price below SMA200',
                    'Price' : 'Over $10',
                    'LT Debt/Equity' : 'Over 0.5',
                    'InstitutionalOwnership' :  'Over 60%',
                    

                    }
    return _run_screener(filters_dict)

def get_short_squeeze_filter():

    filters_dict = {'Float Short': 'Over 15%',
                    'Float' : 'Under 50M',
                    'Option/Short' : 'Shortable',
                    'Insider Transactions' : 'Negative (<0%)'

                    }
    return _run_screener(filters_dict)

def get_fmp_bigger_losers(fmp_api_key):
    fmp_url = f'https://financialmodelingprep.com/stable/biggest-losers?apikey={fmp_api_key}'

    try :
        data = requests.get(fmp_url).json()
        return data
    except Exception as e:
        logging.info(f'Failed to retriefe biggest losers:{str(e)}')
        return []





