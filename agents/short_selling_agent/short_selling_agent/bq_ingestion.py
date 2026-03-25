import os
import logging
from datetime import datetime
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# Absolute imports based on the inner package name
from short_selling_agent.tools import get_blacklist_targets, get_fmp_bigger_losers

logging.basicConfig(level=logging.INFO)

PROJECT_ID = 'datascience-projects'
FMP_API_KEY = os.environ.get("FMP_API_KEY")
DATASET_ID = "finviz_blacklist" 

def setup_bigquery_tables(client: bigquery.Client, dataset_ref):
    """Creates Dataset and Tables if they don't exist."""
    try:
        client.get_dataset(dataset_ref)
    except NotFound:
        logging.info(f"Dataset {DATASET_ID} not found. Creating it...")
        dataset = bigquery.Dataset(dataset_ref)
        dataset.location = "US"
        client.create_dataset(dataset, timeout=30)

    # Blacklist Schema
    blacklist_schema = [
        bigquery.SchemaField("scrape_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("ticker", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("list_type", "STRING", mode="REQUIRED"),
    ]
    blacklist_table_id = f"{PROJECT_ID}.{DATASET_ID}.finviz_snapshots"
    client.create_table(bigquery.Table(blacklist_table_id, schema=blacklist_schema), exists_ok=True)

    # Losers Schema
    losers_schema = [
        bigquery.SchemaField("scrape_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("ticker", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("price", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("change_pct", "FLOAT", mode="NULLABLE"),
    ]
    losers_table_id = f"{PROJECT_ID}.{DATASET_ID}.fmp_daily_losers"
    client.create_table(bigquery.Table(losers_table_id, schema=losers_schema), exists_ok=True)
    
    return blacklist_table_id, losers_table_id


def main():
    logging.info("--- STARTING DAILY INGESTION JOB ---")
    
    if not PROJECT_ID or not FMP_API_KEY:
        logging.error("Missing GCP_PROJECT_ID or FMP_API_KEY environment variables.")
        return

    client = bigquery.Client(project=PROJECT_ID)
    dataset_ref = client.dataset(DATASET_ID)
    blacklist_table_id, losers_table_id = setup_bigquery_tables(client, dataset_ref)
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    
    # 1. INGEST BLACKLIST
    blacklist_report = get_blacklist_targets()
    if getattr(blacklist_report, "error_message", None):
        logging.error(f"Failed to get Blacklist: {blacklist_report.error_message}")
    elif blacklist_report.tickers:
        rows = [{"scrape_date": today_str, "ticker": t, "list_type": "SQUEEZE_BLACKLIST"} for t in blacklist_report.tickers]
        errors = client.insert_rows_json(blacklist_table_id, rows)
        logging.info(f"Saved {len(rows)} Blacklist tickers to BQ." if not errors else f"BQ Errors: {errors}")

    # 2. INGEST FMP LOSERS
    losers_report = get_fmp_bigger_losers()
    if getattr(losers_report, "error_message", None):
        logging.error(f"Failed to get Losers: {losers_report.error_message}")
    elif losers_report.losers:
        rows = [{"scrape_date": today_str, "ticker": l.ticker, "price": l.price, "change_pct": l.change_pct} for l in losers_report.losers]
        errors = client.insert_rows_json(losers_table_id, rows)
        logging.info(f"Saved {len(rows)} FMP Losers to BQ." if not errors else f"BQ Errors: {errors}")

    logging.info("--- INGESTION JOB COMPLETE ---")

if __name__ == "__main__":
    main()