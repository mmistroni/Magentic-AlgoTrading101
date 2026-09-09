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
    """Verifies standard mock execution and ensures no query parameters are sent when reference_date is omitted."""
    # Patch directly on the loaded module object to avoid hyphen-path string lookup errors
    with patch.object(bq_scout_tools, "bigquery") as mock_bq, \
         patch.object(bq_scout_tools, "load_sql_query") as mock_load_sql:
        
        # 1. Setup mock SQL template return
        mock_load_sql.return_value = "SELECT * FROM mock_table"

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

        # 3. Execute the function under test without arguments (no reference_date)
        records = fetch_clinical_signals()

        # 4. Original Assertions
        mock_client_instance.query.assert_called_once()
        assert len(records) == 1
        
        record = records[0]
        assert isinstance(record, ClinicalSignalRecord)
        assert record.ticker == "INCY"
        assert record.failure_status == "TERMINATED"
        assert record.nct_id == "NCT06873789"

        # 5. New Verification: Ensure QueryJobConfig was NOT initialized with parameters when omitted
        # If no reference_date is provided, job_config should either be None or have no query_parameters
        _, kwargs = mock_client_instance.query.call_args
        job_config = kwargs.get("job_config")
        
        if job_config is not None:
            # If a config object was created, verify it contains no query parameters
            mock_bq.QueryJobConfig.assert_called_once()
            _, config_kwargs = mock_bq.QueryJobConfig.call_args
            params = config_kwargs.get("query_parameters")
            assert not params, "Expected zero query parameters when reference_date is omitted."
        else:
            # If job_config is None, it also satisfies the condition that no parameters were injected
            assert job_config is None

def test_fetch_clinical_signals_passes_reference_date():
    """Confirms that the reference_date parameter correctly populates the BigQuery job configuration."""
    with patch.object(bq_scout_tools, "bigquery") as mock_bq, \
         patch.object(bq_scout_tools, "load_sql_query") as mock_load_sql:
        
        mock_load_sql.return_value = "SELECT * FROM mock_table"
        mock_client_instance = mock_bq.Client.return_value
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = []
        mock_client_instance.query.return_value = mock_query_job

        test_anchor = "2025-12-03 23:59:59 UTC"
        
        # Execute tool with reference_date parameter
        fetch_clinical_signals(reference_date=test_anchor)

        # 1. Assert client.query was invoked
        mock_client_instance.query.assert_called_once()
        
        # 2. Verify ScalarQueryParameter was called with the correct arguments
        mock_bq.ScalarQueryParameter.assert_called_once_with(
            "reference_date", "TIMESTAMP", test_anchor
        )
        
        # 3. Verify QueryJobConfig received the parameter list
        mock_bq.QueryJobConfig.assert_called_once()
        _, kwargs = mock_bq.QueryJobConfig.call_args
        assert kwargs.get("query_parameters") is not None

def test_bq_scout_agent_tool_binding():
    """Verifies that the bq_scout_agent and its skill directory are correctly configured."""
    assert bq_scout_agent.name == "BQScoutAgent"
    assert bq_scout_agent.output_key == "clinical_signals"
    assert BQ_SKILL_PATH.exists()
    assert (BQ_SKILL_PATH / "SKILL.md").exists()