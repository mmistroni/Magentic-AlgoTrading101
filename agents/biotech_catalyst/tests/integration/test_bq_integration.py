import importlib.util
import os
from pathlib import Path
import pytest
from datetime import datetime

# Dynamically load the tool script via file path (bypasses hyphenated folder import limitation)
current_dir = Path(__file__).resolve().parent
tool_path = current_dir.parent.parent / "biotech_catalyst" / "skills" / "bq-scout" / "scripts" / "bq_scout_tools.py"

spec = importlib.util.spec_from_file_location("bq_scout_tools", tool_path)
bq_scout_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bq_scout_tools)

fetch_clinical_signals = bq_scout_tools.fetch_clinical_signals

# Import schemas normally
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
        pytest.skip(
            "Skipping BigQuery integration test: GOOGLE_APPLICATION_CREDENTIALS or GCP_PROJECT_ID not set. "
            "Run 'gcloud auth application-default login' or export your service account key path."
        )

    # Define historical anchor date where data is guaranteed to exist
    historical_anchor = "2025-12-03 23:59:59 UTC"

    # Execute the live query
    records = fetch_clinical_signals(reference_date=historical_anchor)

    # Validate results structure and types returned from BigQuery
    assert isinstance(records, list), "Expected a list of clinical signal records."
    
    print(f"Successfully fetched {len(records)} records from BigQuery using historical anchor {historical_anchor}")

    # Validate schema conformity on returned live items
    for record in records:
        assert isinstance(record, ClinicalSignalRecord)
        assert record.ticker is not None
        assert record.failure_status in ('TERMINATED', 'SUSPENDED', 'WITHDRAWN')
        assert isinstance(record.failure_post_date, datetime)