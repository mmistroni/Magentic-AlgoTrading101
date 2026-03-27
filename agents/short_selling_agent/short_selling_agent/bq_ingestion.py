import os
import logging
from datetime import datetime
from google.cloud import bigquery
from google.cloud.exceptions import NotFound

# Absolute imports based on the inner package name
from short_selling_agent.tools import get_fmp_bigger_losers, \
                    get_squeeze_metrics

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

    
    # Losers Schema
    losers_schema = [
        bigquery.SchemaField("scrape_date", "DATE", mode="REQUIRED"),
        bigquery.SchemaField("ticker", "STRING", mode="REQUIRED"),
        bigquery.SchemaField("price", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("change_pct", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("short_interest_pct", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("free_float", "FLOAT", mode="NULLABLE"),
        bigquery.SchemaField("is_squeeze_risk", "BOOLEAN", mode="REQUIRED"),
    ]
    losers_table_id = f"{PROJECT_ID}.{DATASET_ID}.fmp_daily_losers"
    client.create_table(bigquery.Table(losers_table_id, schema=losers_schema), exists_ok=True)
    
    return losers_table_id


def main():
    logging.info("--- STARTING DAILY INGESTION JOB ---")
    
    if not PROJECT_ID or not FMP_API_KEY:
        logging.error("Missing GCP_PROJECT_ID or FMP_API_KEY environment variables.")
        return

    client = bigquery.Client(project=PROJECT_ID)
    dataset_ref = client.dataset(DATASET_ID)
    losers_table_id = setup_bigquery_tables(client, dataset_ref)
    today_str = datetime.utcnow().strftime('%Y-%m-%d')
    
    # 2. INGEST FMP LOSERS
    losers_report = get_fmp_bigger_losers()
    if getattr(losers_report, "error_message", None):
        logging.error(f"Failed to get Losers: {losers_report.error_message}")
    elif losers_report.losers:
        rows_to_insert = []
        for loser in losers_report.losers:
            # Skip penny stocks instantly
            if loser.price < 5.00:
                continue 
                
            # Check the Squeeze Risk
            # Fetch the historical metrics
            short_pct, free_float = get_squeeze_metrics(loser.ticker)
            
            # Determine the risk (Short > 15% AND Float < 50M)
            is_dangerous = bool(short_pct > 15.0 and free_float < 50000000)
            
            rows_to_insert.append({
                "scrape_date": today_str,
                "ticker": loser.ticker,
                "price": loser.price,
                "change_pct": loser.change_pct,
                "short_interest_pct": short_pct,
                "free_float": free_float,
                "is_squeeze_risk": is_dangerous
            })    

        if rows_to_insert:
            errors = client.insert_rows_json(losers_table_id, rows_to_insert)
            if errors:
                logging.error(f"BQ Insert Errors: {errors}")
            else:
                logging.info(f"Saved {len(rows_to_insert)} Enriched Losers to BQ.")
        else:
            logging.warning("No valid stocks (>\$5.00) found today. Nothing saved to BQ.")


    logging.info("--- INGESTION JOB COMPLETE ---")

if __name__ == "__main__":
    main()