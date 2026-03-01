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
        
        params = {
            "filing_year": year,
            "filing_type": q,  # Q1, Q2, Q3, or Q4
            "page_size": 250   # Max allowed by API
        }
        
        next_url = base_url
        page_count = 0
        clean_rows = []
        max_pages = 100  # Safety limit to prevent infinite loops
        consecutive_empty = 0  # Track empty pages
        
        while next_url and page_count < max_pages:
            try:
                # API Call - Use next_url directly for pagination
                if page_count == 0:
                    # First request with parameters
                    resp = requests.get(next_url, params=params)
                else:
                    # Subsequent requests use the full URL from 'next'
                    resp = requests.get(next_url)
                
                # Handle rate limiting
                if resp.status_code == 429:
                    retry_after = int(resp.headers.get('Retry-After', 30))
                    log(f"⏳ Rate limited. Waiting {retry_after} seconds...")
                    time.sleep(retry_after)
                    continue  # Retry the same URL
                
                if resp.status_code != 200:
                    log(f"❌ API Error {resp.status_code}: {resp.text}")
                    break
                
                data = resp.json()
                results = data.get('results', [])
                
                # Check for empty results
                if not results:
                    consecutive_empty += 1
                    if consecutive_empty >= 3:  # Stop after 3 empty pages
                        log(f"   ...stopped after {consecutive_empty} empty pages")
                        break
                else:
                    consecutive_empty = 0  # Reset counter
                
                # Get next URL for pagination
                next_url = data.get('next')
                
                # Process Page
                for item in results:
                    client = item.get('client', {})
                    client_name = client.get('name', '').upper()
                    
                    if not client_name: 
                        continue

                    # Get Amount
                    income = item.get('income')
                    expenses = item.get('expenses')
                    
                    amt = 0.0
                    if income: 
                        amt = float(income)
                    if expenses: 
                        amt = max(amt, float(expenses))
                    
                    # Filter: Only significant spending (> \$10k)
                    if amt < 10000: 
                        continue

                    # Map Ticker
                    ticker = mapper.find_ticker(client_name)
                    if not ticker: 
                        continue

                    # Extract Issues
                    issues = [i.get('general_issue_code', '') for i in item.get('lobbying_activities', [])]
                    issue_str = ",".join(filter(None, issues))

                    clean_rows.append({
                        "filing_year": int(year),
                        "filing_period": q,
                        "client_name": client_name,
                        "ticker": ticker,
                        "amount": amt,
                        "registrant_name": item.get('registrant', {}).get('name'),
                        "general_issues": issue_str,
                        "filing_date": item.get('dt_posted', '')[:10],
                        "description": (item.get('lobbying_activities', [{}])[0].get('description', '') if item.get('lobbying_activities') else '')[:1000]
                    })
                
                page_count += 1
                if page_count % 10 == 0:
                    log(f"   ...scraped {page_count} pages ({len(clean_rows)} rows so far)...")
                
                # Rate limiting - adjust based on API limits
                time.sleep(1.5)  # Increased delay to avoid 429 errors

            except requests.exceptions.RequestException as e:
                log(f"⚠️ Network error on page {page_count}: {e}")
                time.sleep(5)
                continue
            except Exception as e:
                log(f"⚠️ Unexpected error on page {page_count}: {e}")
                break
        
        # Upload Quarter to BigQuery
        if clean_rows:
            log(f'✅ Found {len(clean_rows)} lobbying records for {year}-{q}')
            upsert_to_bigquery(clean_rows)
        else:
            log(f"⚠️ No public company lobbying found for {year}-{q}.")


def upsert_to_bigquery(rows):
    try:
        client = bigquery.Client(project=PROJECT_ID)
        dataset_id = f"{PROJECT_ID}.{DATASET_ID}"
        table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
        
        # Ensure dataset exists
        try:
            client.get_dataset(dataset_id)
        except Exception:
            dataset = bigquery.Dataset(dataset_id)
            dataset.location = "US"
            dataset = client.create_dataset(dataset, exists_ok=True)
            log(f"✅ Created dataset {dataset_id}")
        
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
        
        # Create table if it doesn't exist (using exists_ok)
        table = bigquery.Table(table_id, schema=schema)
        table = client.create_table(table, exists_ok=True)  # Won't error if table exists
        
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