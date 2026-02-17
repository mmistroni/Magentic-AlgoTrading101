import os
import requests
import pandas as pd
import datetime
import time
import argparse
import sys
from google.cloud import bigquery

# --- PATH SETUP ---
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

from ticker_mapper import TickerMapper 

# CONFIG
PROJECT_ID = os.environ.get("PROJECT_ID", "datascience-projects")
DATASET_ID = "gcp_shareloader"
TABLE_ID = "lobbying_signals"

def log(msg):
    print(f"[{datetime.datetime.now()}] {msg}", flush=True)

def fetch_lobbying_data(year, quarters=None):
    """
    Fetches Lobbying Data from the US Senate API.
    """
    if not quarters:
        quarters = ["Q1", "Q2", "Q3", "Q4"]

    log(f"🚀 Starting Lobbying Scraper for Year: {year}, Quarters: {quarters}")

    # 1. Initialize Ticker Mapper
    try:
        mapper = TickerMapper() 
        log(f"✅ Mapper loaded ({len(mapper.mapping)} tickers).")
    except Exception as e:
        log(f"❌ Mapper Critical Failure: {e}")
        return

    # 2. Iterate through Quarters
    base_url = "https://lda.senate.gov/api/v1/filings/"
    
    for q in quarters:
        log(f"🔄 Processing {year} - {q}...")
        
        # We filter by Year, Quarter, and ensure it's a Quarterly Report (RR)
        params = {
            "filing_year": year,
            "filing_period": q,
            "filing_type": "RR", # Regular Report
            "page_size": 250     # Max allowed by API
        }
        
        next_url = base_url
        page_count = 0
        clean_rows = []
        
        while next_url:
            try:
                # API Call
                resp = requests.get(next_url, params=params if next_url == base_url else None)
                if resp.status_code != 200:
                    log(f"❌ API Error {resp.status_code}: {resp.text}")
                    break
                
                data = resp.json()
                results = data.get('results', [])
                next_url = data.get('next') # Pagination URL
                
                if not results:
                    break

                # Process Page
                for item in results:
                    client = item.get('client', {})
                    client_name = client.get('name', '').upper()
                    
                    # 1. Filter: Must be a corporate-sounding client
                    # (Simple heuristic to skip 'Association of...', 'Alliance for...', etc.)
                    if not client_name: continue

                    # 2. Get Amount (Income = Firm hired, Expenses = In-house lobbying)
                    income = item.get('income')
                    expenses = item.get('expenses')
                    
                    # Convert None to 0.0
                    amt = 0.0
                    if income: amt = float(income)
                    if expenses: amt = max(amt, float(expenses))
                    
                    # Filter: Only significant spending (> \$10k)
                    if amt < 10000: continue

                    # 3. Map Ticker (The Critical Step)
                    ticker = mapper.find_ticker(client_name)
                    if not ticker: continue

                    # 4. Extract Issues (What are they lobbying for?)
                    issues = [i.get('general_issue_code', '') for i in item.get('general_issue_codes', [])]
                    issue_str = ",".join(filter(None, issues))

                    clean_rows.append({
                        "filing_year": int(year),
                        "filing_period": q,
                        "client_name": client_name,
                        "ticker": ticker,
                        "amount": amt,
                        "registrant_name": item.get('registrant', {}).get('name'),
                        "general_issues": issue_str,
                        "filing_date": item.get('dt_posted', '')[:10], # YYYY-MM-DD
                        "description": item.get('description', '')[:1000]
                    })
                
                page_count += 1
                if page_count % 10 == 0:
                    log(f"   ...scraped {page_count} pages ({len(clean_rows)} rows so far)...")
                
                # Sleep to respect rate limits
                time.sleep(0.5)

            except Exception as e:
                log(f"⚠️ Error on page {page_count}: {e}")
                time.sleep(5)
        
        # Upload Quarter to BigQuery
        if clean_rows:
            upsert_to_bigquery(clean_rows)
        else:
            log(f"⚠️ No public company lobbying found for {year}-{q}.")

def upsert_to_bigquery(rows):
    try:
        client = bigquery.Client(project=PROJECT_ID)
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
        
        # Schema definition
        schema = [
            bigquery.SchemaField("filing_year", "INTEGER"),
            bigquery.SchemaField("filing_period", "STRING"),
            bigquery.SchemaField("client_name", "STRING"),
            bigquery.SchemaField("ticker", "STRING"),
            bigquery.SchemaField("amount", "FLOAT"),
            bigquery.SchemaField("registrant_name", "STRING"),
            bigquery.SchemaField("general_issues", "STRING"),
            bigquery.SchemaField("filing_date", "DATE"),
            bigquery.SchemaField("description", "STRING"),
        ]
        
        # Load to Temp Table
        temp_table_id = f"{PROJECT_ID}.{DATASET_ID}.temp_lobbying_{int(time.time())}"
        job_config = bigquery.LoadJobConfig(schema=schema, write_disposition="WRITE_TRUNCATE")
        
        job = client.load_table_from_json(rows, temp_table_id, job_config=job_config)
        job.result()
        
        # Deduplication Merge Query
        query = f"""
        MERGE `{table_id}` T
        USING `{temp_table_id}` S
        ON T.ticker = S.ticker 
           AND T.filing_year = S.filing_year 
           AND T.filing_period = S.filing_period
           AND T.registrant_name = S.registrant_name
        WHEN NOT MATCHED THEN
          INSERT (filing_year, filing_period, client_name, ticker, amount, registrant_name, general_issues, filing_date, description)
          VALUES (filing_year, filing_period, client_name, ticker, amount, registrant_name, general_issues, filing_date, description)
        WHEN MATCHED THEN
          UPDATE SET amount = S.amount, filing_date = S.filing_date
        """
        
        client.query(query).result()
        log(f"✅ Upserted {len(rows)} rows to BigQuery.")
        client.delete_table(temp_table_id, not_found_ok=True)
        
    except Exception as e:
        log(f"❌ BigQuery Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--year", type=int, default=2024, help="Year to scrape (e.g., 2024)")
    parser.add_argument("--quarter", type=str, default=None, help="Specific quarter (Q1, Q2, Q3, Q4). Default is all.")
    
    args = parser.parse_args()
    
    quarters = [args.quarter] if args.quarter else None
    fetch_lobbying_data(args.year, quarters)