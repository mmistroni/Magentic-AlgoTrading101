import requests
import pandas as pd
import io
import datetime
from google.cloud import bigquery
import os

# --- CONFIG ---
PROJECT_ID = os.environ.get("PROJECT_ID", "datascience-projects")
DATASET_ID = "gcp_shareloader"
STAGING_TABLE_ID = "senate_disclosures_staging"

# 🚀 The GitHub Raw URL (Cannot be blocked by API limits)
SOURCE_URL = "https://raw.githubusercontent.com/code-for-democracy/senate-stock-watcher-data/main/aggregate/all_transactions.csv"

def fetch_and_stage_senate_data():
    print("🕵️  Fetching Senate Trades from GitHub Mirror...")
    
    try:
        s = requests.get(SOURCE_URL).content
        # Skip bad lines automatically
        df = pd.read_csv(io.StringIO(s.decode('utf-8')), on_bad_lines='skip')
        print(f"✅ Downloaded raw CSV. Total rows: {len(df)}")
    except Exception as e:
        print(f"❌ Failed to download from GitHub: {e}")
        return

    # --- FILTER FOR 2024 ---
    print("🔍 Filtering for 2024...")
    
    # Convert date column
    df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
    
    # Filter: Year 2024 ONLY
    mask_2024 = (df['transaction_date'].dt.year == 2024)
    df_2024 = df[mask_2024].copy()
    
    # Filter: Valid Tickers only (No '--' or empty)
    mask_ticker = (df_2024['ticker'].notna()) & (df_2024['ticker'] != '--')
    df_clean = df_2024[mask_ticker].copy()

    print(f"💎 Found {len(df_clean)} valid Senate trades for 2024.")

    if df_clean.empty:
        print("⚠️ No 2024 data found in this mirror yet.")
        return

    # --- PREPARE FOR BIGQUERY ---
    # Rename columns to match your schema
    # CSV cols: transaction_date, owner, ticker, asset_description, asset_type, type, amount, comment, senator
    
    bq_rows = []
    for _, row in df_clean.iterrows():
        # Clean the Ticker string immediately so it matches Lobbying data
        raw_ticker = str(row['ticker']).strip().upper()
        
        bq_rows.append({
            "AS_OF_DATE": row['transaction_date'].strftime('%Y-%m-%d'),
            "DISCLOSURE": str(row['type']).title(), # e.g. "Purchase"
            "TICKER": raw_ticker,
            "representative": str(row['senator']),
            "amount": str(row['amount'])
        })

    # --- UPLOAD TO STAGING ---
    upload_to_staging(bq_rows)

def upload_to_staging(rows):
    client = bigquery.Client(project=PROJECT_ID)
    table_ref = f"{PROJECT_ID}.{DATASET_ID}.{STAGING_TABLE_ID}"
    
    schema = [
        bigquery.SchemaField("AS_OF_DATE", "DATE"),
        bigquery.SchemaField("DISCLOSURE", "STRING"),
        bigquery.SchemaField("TICKER", "STRING"),
        bigquery.SchemaField("representative", "STRING"),
        bigquery.SchemaField("amount", "STRING")
    ]
    
    job_config = bigquery.LoadJobConfig(
        schema=schema,
        write_disposition="WRITE_TRUNCATE", # Safe: Only wipes staging table
    )

    print(f"📤 Uploading {len(rows)} rows to STAGING table...")
    job = client.load_table_from_json(rows, table_ref, job_config=job_config)
    job.result()
    print("✅ Staging complete!")
    print("👉 Now run the SQL Merge command.")

if __name__ == "__main__":
    fetch_and_stage_senate_data()