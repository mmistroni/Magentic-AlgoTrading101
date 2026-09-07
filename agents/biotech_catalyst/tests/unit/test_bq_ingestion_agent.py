import importlib.util
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# 1. Correct ADK Framework imports
from google.adk.agents import LlmAgent

# 2. Dynamically load the tool script (bypassing the hyphen folder limitation safely)
current_dir = os.path.dirname(os.path.abspath(__file__))
tool_path = os.path.normpath(
    os.path.join(
        current_dir, 
        "../../biotech_catalyst/skills/bq-scout/scripts/bq_scout_tools.py"
    )
)

spec = importlib.util.spec_from_file_location("bq_scout_tools", tool_path)
bq_scout_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bq_scout_tools)

fetch_clinical_signals = bq_scout_tools.fetch_clinical_signals

# 3. Import agent and schemas
from biotech_catalyst.catalyst_agents import (
    bq_scout_agent,
    BQ_SKILL_PATH
)
from schemas import ClinicalSignalRecord


def test_bq_scout_agent_baseline():
    """Baseline test verifying the current LlmAgent setup and skill directory existence."""
    assert isinstance(bq_scout_agent, LlmAgent)
    assert bq_scout_agent.name == "BQScoutAgent"
    assert bq_scout_agent.model == "gemini-2.5-flash"

    assert BQ_SKILL_PATH.exists()
    assert (BQ_SKILL_PATH / "SKILL.md").exists()


class MockBigQueryRow:
    """Mocks a single row returned by BigQuery job results."""
    def __init__(self, row_dict):
        for key, value in row_dict.items():
            setattr(self, key, value)


def test_fetch_clinical_signals_mock():
    # Patch directly on the loaded module object to avoid hyphen-path string lookup errors
    with patch.object(bq_scout_tools, "bigquery") as mock_bq, \
         patch.object(bq_scout_tools, "load_sql_query") as mock_load_sql:
        
        # 1. Setup mock SQL template return
        mock_load_sql.return_value = "SELECT * FROM `{project_id}.{dataset_id}.{table_id}`"

        # 2. Setup mock BigQuery client and query result rows
        mock_client_instance = mock_bq.Client.return_value
        mock_query_job = MagicMock()
        
        fake_row_data = {
            "ticker": "INCY",
            "cusip": "45337C102",
            "sponsor": "Incyte Corporation",
            "failure_status": "TERMINATED",
            "failure_post_date": datetime(2026, 9, 3, 6, 3, 19),
            "nct_id": "NCT06873789",
            "trial_title": "A Study to Evaluate INCB177054",
            "failure_reason": "Strategic business decision."
        }
        
        mock_query_job.result.return_value = [MockBigQueryRow(fake_row_data)]
        mock_client_instance.query.return_value = mock_query_job

        # 3. Execute the function under test
        records = fetch_clinical_signals("test-project", "biotech_catalysts", "signals")

        # 4. Assertions
        mock_client_instance.query.assert_called_once()
        assert len(records) == 1
        
        record = records[0]
        assert isinstance(record, ClinicalSignalRecord)
        assert record.ticker == "INCY"
        assert record.failure_status == "TERMINATED"
        assert record.nct_id == "NCT06873789"