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

import requests

def get_short_squeeze_filter():
    print("Injecting stealth headers for Cloud Run...")
    
    # 1. The Disguise: Make Python look exactly like a real Desktop Chrome Browser
    stealth_headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'en-US,en;q=0.5',
        'Upgrade-Insecure-Requests': '1',
        'Sec-Fetch-Dest': 'document',
        'Sec-Fetch-Mode': 'navigate',
        'Sec-Fetch-Site': 'none',
        'Sec-Fetch-User': '?1',
        'Cache-Control': 'max-age=0'
    }
    
    # 2. Apply the disguise globally to the underlying requests library
    requests.utils.default_headers().update(stealth_headers)

    # 3. Your exact filters
    filters_dict = {
        'Float Short': 'Over 15%',
        'Float' : 'Under 50M',
        'Option/Short' : 'Shortable',
        'InsiderTransactions' : 'Negative (<0%)' 
    }
    
    # 4. Execute your existing screener logic
    return _run_screener(filters_dict)





