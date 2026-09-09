import os
import pytest
from datetime import datetime

# Import your real fetch function (using the same loader logic or relative import)
from biotech_catalyst.skills.bq_scout.scripts.bq_scout_tools import fetch_clinical_signals
from schemas import ClinicalSignalRecord

@pytest.mark.integration
def test_real_bigquery_clinical_signals_integration():
    """
    Performs a real roundtrip query against BigQuery.
    Anchored to December 3, 2025 to align with available historical test data
    and bypass the 5-day CURRENT_TIMESTAMP() window limitation.
    """
    # Ensure GCP authentication environment variable is available
    if not os.getenv("GOOGLE_APPLICATION_CREDENTIALS") and not os.getenv("GCP_PROJECT_ID"):
        pytest.skip("Skipping BigQuery integration test: GCP credentials not found in environment.")

    # Define a historical anchor date where data is guaranteed to exist in your table
    historical_anchor = "2025-12-03 23:59:59 UTC"

    # Execute the live query
    records = fetch_clinical_signals(reference_date=historical_anchor)

    # Validate the results structure and types returned from BigQuery
    assert isinstance(records, list), "Expected a list of clinical signal records."
    
    print(f"Successfully fetched {len(records)} records from BigQuery using historical anchor {historical_anchor}")

    # If records exist in that window, validate schema conformity
    for record in records:
        assert isinstance(record, ClinicalSignalRecord)
        assert record.ticker is not None
        assert record.failure_status in ('TERMINATED', 'SUSPENDED', 'WITHDRAWN')
        assert isinstance(record.failure_post_date, datetime)