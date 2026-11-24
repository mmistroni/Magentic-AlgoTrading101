import os
import logging
import math
from datetime import date, datetime
import numpy as np
import pandas as pd
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

def _to_json_safe(value):
    if value is None:
        return None
    if isinstance(value, (pd.Timestamp, datetime, date)):
        return value.isoformat()
    if isinstance(value, (np.integer, int)):
        return int(value)
    if isinstance(value, (np.floating, float)):
        val = float(value)
        return None if math.isnan(val) or math.isinf(val) else val
    if isinstance(value, (np.bool_, bool)):
        return bool(value)
    if isinstance(value, dict):
        return {str(k): _to_json_safe(v) for k, v in value.items()}
    if isinstance(value, (list, tuple, np.ndarray)):
        return [_to_json_safe(item) for item in value]
    if pd.isna(value):
        return None
    return value


def _log_schema_diff(client: bigquery.Client, rows: list[dict], table_id: str) -> set[str]:
    table = client.get_table(table_id)
    bq_fields = {field.name for field in table.schema}
    logger.info(f"BigQuery schema columns ({len(bq_fields)}): {sorted(bq_fields)}")

    for idx, row in enumerate(rows):
        row_keys = set(row.keys())
        extra_keys = sorted(row_keys - bq_fields)
        missing_keys = sorted(bq_fields - row_keys)
        logger.info(
            f"Row[{idx}] symbol={row.get('symbol')} keys={sorted(row_keys)} "
            f"extra_not_in_bq={extra_keys} missing_in_row={missing_keys}"
        )

    return bq_fields


def save_results_to_bigquery(results: list[dict], table_id: str):
    """Loads pipeline result records into BigQuery."""
    if not results:
        logger.info("No records to save to BigQuery.")
        return

    if isinstance(results, pd.DataFrame):
        raw_rows = results.to_dict(orient="records")
    else:
        raw_rows = results

    sanitized_rows = []
    for idx, row in enumerate(raw_rows):
        if not isinstance(row, dict):
            logger.warning(f"Skipping non-dict row at index {idx}: {type(row).__name__}")
            continue
        sanitized_rows.append(_to_json_safe(row))

    if not sanitized_rows:
        logger.warning("No valid dict rows remaining after sanitization; skipping BigQuery load.")
        return
    
    client = bigquery.Client()

    ## logging
    logger.info(f"Preparing to load {len(sanitized_rows)} records into BigQuery table: {table_id}")

    bq_fields = _log_schema_diff(client, sanitized_rows, table_id)
    aligned_rows = [
        {col: row.get(col) for col in bq_fields if col in row}
        for row in sanitized_rows
]


    
    # Configure load job (WRITE_APPEND or WRITE_TRUNCATE)
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_APPEND,
        autodetect=False 
    )

    logger.info(f"💾 Storing {len(aligned_rows)} records into BigQuery table: {table_id}")
    job = client.load_table_from_json(aligned_rows, table_id, job_config=job_config)
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