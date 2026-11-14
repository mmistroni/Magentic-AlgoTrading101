import os
import logging
from google.cloud import bigquery
from ingest_fmp.pipeline import (
    run_eod_screener,
    get_extra_watchlist,
    run_market_down_pipeline,
    run_high_growth_float_watchlist,
    run_swing_trading_pipeline,
    run_new_highs_pipeline
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

PIPELINE_REGISTRY = {
    "eod": run_eod_screener,
    "extra": get_extra_watchlist,
    "market_down": run_market_down_pipeline,
    "high_growth_float": run_high_growth_float_watchlist,
    "swing_trading": run_swing_trading_pipeline,
    "new_highs": run_new_highs_pipeline,
}

def save_results_to_bigquery(results: list[dict], table_id: str):
    """Loads pipeline result records into BigQuery."""
    if not results:
        logger.warning("⚠️ No records returned from pipeline. Skipping BigQuery load.")
        return

    client = bigquery.Client()
    
    # Configure load job (WRITE_APPEND or WRITE_TRUNCATE)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=False 
    )

    logger.info(f"💾 Storing {len(results)} records into BigQuery table: {table_id}")
    job = client.load_table_from_json(results, table_id, job_config=job_config)
    job.result()  # Wait for the BigQuery load job to complete
    logger.info(f"✅ Successfully loaded records into BigQuery table {table_id}")

def main():
    pipeline_name = os.environ.get("PIPELINE_NAME", "eod").lower()
    raw_limit = os.environ.get("LIMIT")
    limit = int(raw_limit) if raw_limit else None
    
    # BigQuery table destination (e.g. project.dataset.tmp_table)
    bigquery_table = os.environ.get("BIGQUERY_TABLE_ID")

    if pipeline_name not in PIPELINE_REGISTRY:
        logger.error(f"❌ Unknown pipeline '{pipeline_name}'. Choose from: {list(PIPELINE_REGISTRY.keys())}")
        exit(1)

    logger.info(f"🚀 Starting Cloud Run Job for pipeline: '{pipeline_name}' (limit={limit})")
    
    pipeline_func = PIPELINE_REGISTRY[pipeline_name]
    
    # Execute pipeline
    if limit is not None:
        results = pipeline_func(limit=limit)
    else:
        results = pipeline_func()

    logger.info(f"📊 Pipeline '{pipeline_name}' completed. Generated {len(results)} records.")

    # Persist to BigQuery if table destination is provided
    if bigquery_table:
        save_results_to_bigquery(results, bigquery_table)
    else:
        logger.info("ℹ️ BIGQUERY_TABLE_ID not set. Skipping persistence to BigQuery.")

if __name__ == "__main__":
    main()