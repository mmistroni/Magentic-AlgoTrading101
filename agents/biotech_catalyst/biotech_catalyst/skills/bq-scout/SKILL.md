---
name: bq-scout
description: Queries BigQuery for terminated or suspended clinical trial signals over a 3-day lookback window or around an optional reference date.
---

# Skill: BigQuery Clinical Trial Scout (`bq_scout_tools`)

## Description
This skill queries BigQuery to extract high-polarity, negative clinical trial catalysts (`TERMINATED` or `SUSPENDED`) over a rolling 3-day lookback window (or anchored to a supplied `reference_date` for testing and backfills). It acts as the ingestion engine for the biotech catalyst pipeline.

## Operational Workflow
1. **Determine Date Window**:
   - If an explicit `reference_date` is provided (for testing, backfilling, or historical checks), pass it to the tool.
   - If no date is specified, omit `reference_date` to use the live rolling 3-day lookback (`TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)`).
2. **Load SQL Query**: Read the query template located at `resources/bq.sql`.
3. **Execute BigQuery Client**: Run the parameterized query against the configured GCP dataset/table.
4. **Validate & Report**: Parse rows through `ClinicalSignalRecord` / `ClinicalSignalResponse`, preserve exact tickers, NCT IDs, and reasons without inventing data, and clearly state when no signals are returned.