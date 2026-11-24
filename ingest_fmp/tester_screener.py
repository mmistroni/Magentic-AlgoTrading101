import os
import requests

API_KEY = os.environ["FMP_KEY"]
BASE_URL = "https://financialmodelingprep.com/stable/company-screener"

exchanges_to_test = ["NYSE", "NASDAQ", "AMEX"]

for exch in exchanges_to_test:
    params = {
        "exchange": exch,
        "isActivelyTrading": True,
        "isEtf": False,
        "isFund": False,
        "limit": 5000,
        "apikey": API_KEY,
    }
    resp = requests.get(BASE_URL, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()
    symbols = [row.get("symbol") for row in data if row.get("symbol")]
    print(f"Exchange={exch}: {len(symbols)} symbols returned (sample: {symbols[:5]})")