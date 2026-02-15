import requests
import zipfile
import pandas as pd
from io import BytesIO

# 1. Download a small recent file
print("⬇️ Downloading sample contract file...")
# This is a direct link to a recent daily file (or we generate one)
# Since we need a valid URL, let's use the API to generate one quickly
url = "https://api.usaspending.gov/api/v2/bulk_download/awards/"
payload = {
    "filters": {
        "prime_award_types": ["A"], 
        "date_type": "action_date",
        "date_range": {"start_date": "2024-01-01", "end_date": "2024-01-02"}
    },
    "file_format": "csv"
}
resp = requests.post(url, json=payload).json()
file_url = resp['file_url']

print(f"URL: {file_url}")
# Wait for generation (manual sleep usually works for small files)
import time
time.sleep(20) 

r = requests.get(file_url)
if not r.content.startswith(b'PK'):
    print("❌ File not ready yet. Run again.")
else:
    with zipfile.ZipFile(BytesIO(r.content)) as z:
        fname = z.namelist()[0]
        with z.open(fname) as f:
            # Read just the header
            df = pd.read_csv(f, nrows=1)
            print("\n📋 FOUND COLUMN NAMES:")
            print(list(df.columns))
            
            # Check specifically for amount columns
            print("\n💰 LOOKING FOR AMOUNT COLUMNS:")
            for col in df.columns:
                if 'obligation' in col.lower() or 'amount' in col.lower() or 'dollars' in col.lower():
                    print(f"   -> {col}")