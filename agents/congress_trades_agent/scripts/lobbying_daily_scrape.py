#!/usr/bin/env python3
"""
Daily Lobbying Data Downloader
Downloads new/updated lobbying filings from the Senate LDA API.
Designed to run daily via cron/scheduler to catch new filings as they come in.
"""

import os
import sys
import requests
import pandas as pd
import datetime
from datetime import timedelta
import time
import logging
from pathlib import Path
from google.cloud import bigquery
import json

# --- CONFIGURATION ---
PROJECT_ID = os.environ.get("PROJECT_ID", "datascience-projects")
DATASET_ID = "gcp_shareloader"
TABLE_ID = "lobbying_signals"

# Setup logging
log_dir = Path("/tmp/lobbying_logs")
log_dir.mkdir(exist_ok=True, parents=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_dir / f"daily_download_{datetime.date.today()}.log"),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Add parent directory to path for ticker_mapper import
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(current_dir)

try:
    from ticker_mapper import TickerMapper
except ImportError:
    logger.error("Could not import TickerMapper. Make sure ticker_mapper.py is in the same directory.")
    sys.exit(1)

class DailyLobbyingDownloader:
    """
    Daily downloader for lobbying data.
    Focuses on getting the most recent filings.
    """
    
    def __init__(self):
        self.base_url = "https://lda.senate.gov/api/v1/filings/"
        self.mapper = None
        self.stats = {
            'new_filings': 0,
            'updated_filings': 0,
            'total_processed': 0,
            'api_calls': 0,
            'companies_found': 0
        }
        
    def initialize_mapper(self):
        """Initialize the ticker mapper"""
        try:
            self.mapper = TickerMapper()
            logger.info(f"✅ Ticker mapper loaded ({len(self.mapper.mapping)} tickers)")
            return True
        except Exception as e:
            logger.error(f"Failed to load ticker mapper: {e}")
            return False
    
    def get_latest_filing_date_from_db(self):
        """
        Get the most recent filing date from BigQuery to know where to start.
        """
        try:
            client = bigquery.Client(project=PROJECT_ID)
            table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
            
            query = f"""
            SELECT 
                MAX(filing_date) as latest_filing,
                COUNT(*) as total_records,
                MAX(PARSE_DATETIME('%Y-%m-%d %H:%M:%S', 
                    CONCAT(CAST(filing_date AS STRING), ' 00:00:00'))) as latest_datetime
            FROM `{table_id}`
            """
            
            result = client.query(query).result()
            for row in result:
                if row.latest_filing:
                    logger.info(f"📊 Latest filing in database: {row.latest_filing} "
                              f"(Total records: {row.total_records})")
                    return row.latest_filing
                else:
                    logger.info("📊 No existing data in database")
                    # If no data, start from 30 days ago
                    return datetime.date.today() - timedelta(days=30)
                    
        except Exception as e:
            logger.warning(f"Could not check database: {e}")
            # Default to checking last 7 days if can't connect
            return datetime.date.today() - timedelta(days=7)
    
    def determine_date_range(self):
        """
        Determine what date range to fetch.
        For daily runs, we want to catch:
        1. New filings from today
        2. Late filings from the past few days
        3. Any amendments to recent filings
        """
        latest_db_date = self.get_latest_filing_date_from_db()
        today = datetime.date.today()
        
        # Go back a few extra days to catch amendments and late filings
        # Lobbying reports can be amended days after initial filing
        buffer_days = 5
        
        if latest_db_date:
            # Start from a few days before our last record
            start_date = latest_db_date - timedelta(days=buffer_days)
        else:
            # First run - get last 30 days
            start_date = today - timedelta(days=30)
        
        # Don't go too far back on daily runs
        max_lookback = today - timedelta(days=60)
        if start_date < max_lookback:
            start_date = max_lookback
            
        logger.info(f"📅 Date range: {start_date} to {today}")
        return start_date, today
    
    def fetch_filings_by_date_range(self, start_date, end_date):
        """
        Fetch filings within a date range.
        The Senate API allows filtering by posted date.
        """
        all_filings = []
        
        # The API uses dt_posted for when the filing was posted
        # We'll fetch by different filing types to get everything
        filing_types = [
            "Q1", "Q2", "Q3", "Q4",  # Quarterly reports
            "MYR", "YE",              # Mid-year and Year-end reports
            "RR", "RA",               # Registrations and amendments
            "TR"                      # Terminations
        ]
        
        # For daily runs, focus on the current year's filing types
        current_year = datetime.date.today().year
        current_quarter = (datetime.date.today().month - 1) // 3 + 1
        
        # Determine which filing types are most relevant now
        if current_quarter == 1:
            # In Q1, check Q4 from last year and Q1 current year
            priority_types = ["Q1", "Q4", "YE", "RR", "RA"]
        elif current_quarter == 2:
            priority_types = ["Q2", "Q1", "MYR", "RR", "RA"]
        elif current_quarter == 3:
            priority_types = ["Q3", "Q2", "MYR", "RR", "RA"]
        else:  # Q4
            priority_types = ["Q4", "Q3", "YE", "RR", "RA"]
        
        logger.info(f"🔍 Checking filing types: {priority_types}")
        
        for filing_type in priority_types:
            logger.info(f"  Fetching {filing_type} filings...")
            filings = self.fetch_filings_by_type_and_date(
                filing_type, 
                start_date, 
                end_date,
                current_year
            )
            all_filings.extend(filings)
            
            # Rate limiting
            time.sleep(2)
        
        return all_filings
    
    def fetch_filings_by_type_and_date(self, filing_type, start_date, end_date, year):
        """
        Fetch filings of a specific type within date range.
        """
        filings = []
        
        params = {
            "filing_year": year,
            "filing_type": filing_type,
            "page_size": 250
        }
        
        # Also check previous year for Q4/Year-end if we're in Q1
        years_to_check = [year]
        if datetime.date.today().month <= 3 and filing_type in ["Q4", "YE"]:
            years_to_check.append(year - 1)
        
        for check_year in years_to_check:
            params["filing_year"] = check_year
            next_url = self.base_url
            page_count = 0
            max_pages = 10  # Daily runs shouldn't need many pages
            consecutive_empty = 0
            
            while next_url and page_count < max_pages:
                try:
                    self.stats['api_calls'] += 1
                    
                    if page_count == 0:
                        resp = requests.get(next_url, params=params, timeout=30)
                    else:
                        resp = requests.get(next_url, timeout=30)
                    
                    # Handle rate limiting
                    if resp.status_code == 429:
                        retry_after = int(resp.headers.get('Retry-After', 30))
                        logger.warning(f"    Rate limited. Waiting {retry_after} seconds...")
                        time.sleep(retry_after)
                        continue
                    
                    if resp.status_code != 200:
                        logger.error(f"    API Error {resp.status_code}")
                        break
                    
                    data = resp.json()
                    results = data.get('results', [])
                    
                    if not results:
                        consecutive_empty += 1
                        if consecutive_empty >= 2:
                            break
                    else:
                        consecutive_empty = 0
                    
                    # Filter by date
                    for item in results:
                        dt_posted = item.get('dt_posted', '')
                        if dt_posted:
                            posting_date = datetime.datetime.strptime(
                                dt_posted[:10], 
                                '%Y-%m-%d'
                            ).date()
                            
                            # Check if within our date range
                            if start_date <= posting_date <= end_date:
                                filings.append(item)
                                self.stats['total_processed'] += 1
                    
                    # Get next page
                    next_url = data.get('next')
                    page_count += 1
                    
                    # Rate limiting
                    time.sleep(1.5)
                    
                except Exception as e:
                    logger.error(f"    Error fetching {filing_type}: {e}")
                    break
            
            if filings:
                logger.info(f"    Found {len(filings)} {filing_type} filings for year {check_year}")
        
        return filings
    
    def process_filings(self, filings):
        """
        Process raw filings and extract relevant data.
        """
        clean_rows = []
        
        for item in filings:
            try:
                client = item.get('client', {})
                client_name = client.get('name', '').upper()
                
                if not client_name:
                    continue
                
                # Get amount
                income = item.get('income')
                expenses = item.get('expenses')
                amt = 0.0
                if income:
                    amt = float(income)
                if expenses:
                    amt = max(amt, float(expenses))
                
                # Filter: Only significant spending
                if amt < 10000:
                    continue
                
                # Map to ticker
                ticker = self.mapper.find_ticker(client_name)
                if not ticker:
                    continue
                
                self.stats['companies_found'] += 1
                
                # Extract filing period from the filing type
                filing_type = item.get('filing_type', '')
                filing_year = item.get('filing_year', '')
                
                # Determine filing period
                if filing_type in ['Q1', 'Q2', 'Q3', 'Q4']:
                    filing_period = filing_type
                elif filing_type == 'MYR':
                    filing_period = 'MYR'
                elif filing_type == 'YE':
                    filing_period = 'YE'
                else:
                    filing_period = filing_type
                
                # Extract issues from lobbying activities
                issues = []
                for activity in item.get('lobbying_activities', []):
                    issue_code = activity.get('general_issue_code')
                    if issue_code:
                        issues.append(issue_code)
                
                # Get description from first activity
                description = ''
                if item.get('lobbying_activities'):
                    description = item['lobbying_activities'][0].get('description', '')
                
                clean_rows.append({
                    "filing_year": int(filing_year) if filing_year else None,
                    "filing_period": filing_period,
                    "client_name": client_name,
                    "ticker": ticker,
                    "amount": amt,
                    "registrant_name": item.get('registrant', {}).get('name', ''),
                    "general_issues": ",".join(issues[:5]),  # Limit to 5 issues
                    "filing_date": item.get('dt_posted', '')[:10],
                    "description": description[:1000] if description else ''
                })
                
            except Exception as e:
                logger.error(f"Error processing filing: {e}")
                continue
        
        return clean_rows
    
    def upsert_to_bigquery(self, rows):
        """
        Upsert rows to BigQuery, handling duplicates and updates.
        """
        if not rows:
            logger.info("No rows to upload")
            return
        
        try:
            client = bigquery.Client(project=PROJECT_ID)
            dataset_id = f"{PROJECT_ID}.{DATASET_ID}"
            table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_ID}"
            
            # Ensure dataset exists
            try:
                client.get_dataset(dataset_id)
            except:
                dataset = bigquery.Dataset(dataset_id)
                dataset.location = "US"
                dataset = client.create_dataset(dataset, exists_ok=True)
                logger.info(f"Created dataset {dataset_id}")
            
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
            
            # Create table if it doesn't exist
            table = bigquery.Table(table_id, schema=schema)
            table = client.create_table(table, exists_ok=True)
            
            # Load to temp table
            temp_table_id = f"{PROJECT_ID}.{DATASET_ID}.temp_daily_lobbying_{int(time.time())}"
            job_config = bigquery.LoadJobConfig(
                schema=schema,
                write_disposition="WRITE_TRUNCATE"
            )
            
            job = client.load_table_from_json(rows, temp_table_id, job_config=job_config)
            job.result()
            
            # Count what we're about to merge
            count_query = f"""
            SELECT 
                COUNT(*) as new_records,
                COUNT(DISTINCT ticker) as unique_companies,
                SUM(amount) as total_amount
            FROM `{temp_table_id}`
            """
            
            count_result = client.query(count_query).result()
            for row in count_result:
                logger.info(f"📊 Merging: {row.new_records} records, "
                          f"{row.unique_companies} companies, "
                          f"${row.total_amount:,.0f} total")
            
            # Merge query - will update if filing date is newer
            merge_query = f"""
            MERGE `{table_id}` T
            USING `{temp_table_id}` S
            ON T.ticker = S.ticker 
               AND T.filing_year = S.filing_year 
               AND T.filing_period = S.filing_period
               AND T.registrant_name = S.registrant_name
               AND T.client_name = S.client_name
            WHEN NOT MATCHED THEN
              INSERT (filing_year, filing_period, client_name, ticker, amount, 
                      registrant_name, general_issues, filing_date, description)
              VALUES (filing_year, filing_period, client_name, ticker, amount, 
                      registrant_name, general_issues, filing_date, description)
            WHEN MATCHED AND S.filing_date > T.filing_date THEN
              UPDATE SET 
                amount = S.amount,
                filing_date = S.filing_date,
                general_issues = S.general_issues,
                description = S.description
            """
            
            merge_job = client.query(merge_query)
            merge_result = merge_job.result()
            
            # Check how many were new vs updated
            self.stats['new_filings'] = merge_result.num_dml_affected_rows
            
            logger.info(f"✅ Successfully merged {len(rows)} rows to BigQuery "
                       f"({merge_result.num_dml_affected_rows} affected)")
            
            # Cleanup temp table
            client.delete_table(temp_table_id, not_found_ok=True)
            
        except Exception as e:
            logger.error(f"BigQuery error: {e}")
            raise
    
    def save_stats(self):
        """
        Save run statistics for monitoring.
        """
        stats_file = log_dir / "daily_stats.json"
        
        try:
            # Load existing stats
            if stats_file.exists():
                with open(stats_file, 'r') as f:
                    all_stats = json.load(f)
            else:
                all_stats = {}
            
            # Add today's stats
            all_stats[str(datetime.date.today())] = {
                **self.stats,
                'timestamp': datetime.datetime.now().isoformat(),
                'success': True
            }
            
            # Keep only last 30 days
            cutoff = datetime.date.today() - timedelta(days=30)
            all_stats = {
                date: stats for date, stats in all_stats.items()
                if datetime.date.fromisoformat(date) >= cutoff
            }
            
            # Save
            with open(stats_file, 'w') as f:
                json.dump(all_stats, f, indent=2)
                
        except Exception as e:
            logger.error(f"Could not save stats: {e}")
    
    def run(self):
        """
        Main execution method for daily download.
        """
        start_time = datetime.datetime.now()
        
        try:
            logger.info("=" * 70)
            logger.info("🚀 STARTING DAILY LOBBYING DOWNLOAD")
            logger.info(f"Time: {start_time}")
            logger.info("=" * 70)
            
            # Initialize mapper
            if not self.initialize_mapper():
                return False
            
            # Determine date range
            start_date, end_date = self.determine_date_range()
            
            # Fetch filings
            logger.info("📥 Fetching recent filings...")
            filings = self.fetch_filings_by_date_range(start_date, end_date)
            
            if not filings:
                logger.info("No new filings found for the date range")
                return True
            
            logger.info(f"📄 Found {len(filings)} total filings to process")
            
            # Process filings
            logger.info("🔄 Processing filings...")
            clean_rows = self.process_filings(filings)
            
            if not clean_rows:
                logger.info("No relevant company filings found (after ticker mapping)")
                return True
            
            logger.info(f"✅ Processed {len(clean_rows)} relevant company filings")
            
            # Upload to BigQuery
            logger.info("📤 Uploading to BigQuery...")
            self.upsert_to_bigquery(clean_rows)
            
            # Calculate duration
            duration = (datetime.datetime.now() - start_time).total_seconds()
            
            # Final summary
            logger.info("=" * 70)
            logger.info("✅ DAILY DOWNLOAD COMPLETE")
            logger.info(f"   Duration: {duration:.1f} seconds")
            logger.info(f"   API Calls: {self.stats['api_calls']}")
            logger.info(f"   Filings Processed: {self.stats['total_processed']}")
            logger.info(f"   Companies Found: {self.stats['companies_found']}")
            logger.info(f"   New/Updated in DB: {self.stats['new_filings']}")
            logger.info("=" * 70)
            
            # Save stats
            self.save_stats()
            
            return True
            
        except Exception as e:
            logger.error(f"Daily download failed: {e}", exc_info=True)
            self.stats['success'] = False
            self.save_stats()
            return False

def main():
    """
    Main entry point for the script.
    """
    downloader = DailyLobbyingDownloader()
    success = downloader.run()
    sys.exit(0 if success else 1)

if __name__ == "__main__":
    main()