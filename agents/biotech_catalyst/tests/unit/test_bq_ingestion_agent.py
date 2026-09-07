import pytest
from pathlib import Path
from google.adk.agents import LlmAgent
from google.adk.tools import FunctionTool
# Import your tool function (adjust import path based on your directory structure)
from biotech_catalyst.skills.bq_scout.scripts.fetch_clinical_signals import fetch_clinical_signals

# Import the current agent and instruction string
from biotech_catalyst.catalyst_agents import (
    bq_scout_agent,
    BQ_SKILL_PATH
)


def test_bq_scout_agent_baseline():
    """Baseline test verifying the current LlmAgent setup and skill directory existence."""
    # 1. Verify agent type, name, and model
    assert isinstance(bq_scout_agent, LlmAgent)
    assert bq_scout_agent.name == "BQScoutAgent"
    assert bq_scout_agent.model == "gemini-2.5-flash"

    # 2. Verify the skill directory and SKILL.md file exist on disk
    assert BQ_SKILL_PATH.exists()
    assert (BQ_SKILL_PATH / "SKILL.md").exists()

class MockBigQueryRow:
    """Mocks a single row returned by BigQuery job results."""
    def __init__(self, row_dict):
        for key, value in row_dict.items():
            setattr(self, key, value)

class MockBigQueryRow:
    """Mocks a single row returned by BigQuery job results."""
    def __init__(self, row_dict):
        for key, value in row_dict.items():
            setattr(self, key, value)

@patch("scripts.bq_scout_tool.bigquery.Client")
@patch("scripts.bq_scout_tool.load_sql_query")
def test_fetch_clinical_signals_mock(mock_load_sql, mock_bq_client_class):
    # 1. Setup mock SQL template return
    mock_load_sql.return_value = "SELECT * FROM `{project_id}.{dataset_id}.{table_id}`"

    # 2. Setup mock BigQuery client and query result rows
    mock_client_instance = mock_bq_client_class.return_value
    mock_query_job = MagicMock()
    
    # Define fake clinical trial record matching your actual BigQuery columns
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

    # 4. Assertions to verify the script invokes BigQuery and parses correctly
    mock_client_instance.query.assert_called_once()
    assert len(records) == 1
    
    record = records[0]
    assert isinstance(record, ClinicalSignalRecord)
    assert record.ticker == "INCY"
    assert record.failure_status == "TERMINATED"
    assert record.nct_id == "NCT06873789"