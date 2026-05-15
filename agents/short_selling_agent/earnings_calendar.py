# test_earning_calendar.py
import os
import requests
from datetime import datetime, timedelta

FMP_API_KEY = os.environ.get("FMP_API_KEY")
if not FMP_API_KEY:
    print("❌ FMP_API_KEY not set")
    exit()

# Pick a high-earnings day
date = "2025-10-25"  # 🗓️ Apple, Amazon, Meta, Google
other = "2025-12-10"
url = (
    f"https://financialmodelingprep.com/stable/earnings-calendar?apikey={FMP_API_KEY}&from={date}&to={other}"
)

print(f"📡 Fetching: {url}")
response = requests.get(url, timeout=10)
print(f"📊 Status: {response.status_code}")

if response.status_code != 200:
    print(f"❌ Error: {response.text}")
else:
    data = response.json()
    print(f"✅ Found {len(data)} records:")
    for e in data:
        if e.get("percentage", 0) < -5.0:  # >5% drop
            print(f"  💥 {e.get('ticker')}: {e.get('percentage')}% (${e.get('close')})")