---
name: bq-scout
description: Queries BigQuery for terminated or suspended clinical trial signals over a 3-day lookback window.
---

# Skill: BigQuery Clinical Trial Scout (`bq-scout-skill`)

## Description
This skill queries BigQuery to extract high-polarity, negative clinical trial catalysts (`TERMINATED` or `SUSPENDED`) over a rolling lookback window. It acts as the "Daily Sniper" ingestion engine for the biotech short-selling pipeline.

## Operational Workflow
1. **Load SQL Query**: Read the query template located at `resources/bq.sql`.
2. **Execute BigQuery Client**: Connect to the GCP project and run the parameterized query using a 3-day lookback window (`TIMESTAMP_SUB(CURRENT_TIMESTAMP(), INTERVAL 3 DAY)`).
3. **Validate Data**: Parse raw table rows through the `ClinicalSignalRecord` Pydantic model to enforce strict data types.