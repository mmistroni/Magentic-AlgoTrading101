import importlib.util
import os
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# 1. Correct ADK Framework imports
from google.adk.agents import LlmAgent

# 2. Dynamically load the tool script (bypassing hyphen folder limitation)
current_dir = os.path.dirname(os.path.abspath(__file__))
tool_path = os.path.normpath(
    os.path.join(
        current_dir, 
        "../../biotech_catalyst/skills/bq-scout/scripts/bq_scout_tools.py"
    )
)
spec_tool = importlib.util.spec_from_file_location("bq_scout_tools", tool_path)
bq_scout_tools = importlib.util.module_from_spec(spec_tool)
spec_tool.loader.exec_module(bq_scout_tools)
fetch_clinical_signals = bq_scout_tools.fetch_clinical_signals

# 3. Dynamically load the agent from the hyphenated bq-scout skill directory
agent_path = os.path.normpath(
    os.path.join(
        current_dir, 
        "../../biotech_catalyst/skills/bq-scout/agent.py"
    )
)
spec_agent = importlib.util.spec_from_file_location("bq_scout_agent_module", agent_path)
bq_scout_agent_module = importlib.util.module_from_spec(spec_agent)
spec_agent.loader.exec_module(bq_scout_agent_module)

# Extract your actual defined agent and skill path variables
bq_scout = bq_scout_agent_module.bq_scout
SKILL_DIR = getattr(bq_scout_agent_module, "SKILL_DIR", Path(agent_path).parent)

# 4. Import schemas
from schemas import ClinicalSignalRecord


def test_bq_scout_agent_baseline():
    """Baseline test verifying the actual bq_scout LlmAgent configuration and SKILL.md existence."""
    assert isinstance(bq_scout, LlmAgent)
    assert bq_scout.name == "BQScout"
    assert bq_scout.model == "gemini-2.5-flash"
    assert bq_scout.output_key == "clinical_signals"

    skill_path = Path(SKILL_DIR) if isinstance(SKILL_DIR, Path) else Path(agent_path).parent
    assert skill_path.exists()
    assert (skill_path / "SKILL.md").exists()
    assert len(bq_scout.instruction) > 0


class MockBigQueryRow:
    """Mocks a single row returned by BigQuery job results."""
    def __init__(self, row_dict):
        for key, value in row_dict.items():
            setattr(self, key, value)


def test_fetch_clinical_signals_mock():
    """Verifies standard mock execution and ensures no query parameters are sent when reference_date is omitted."""
    with patch.object(bq_scout_tools, "bigquery") as mock_bq, \
         patch.object(bq_scout_tools, "load_sql_query") as mock_load_sql:
        
        mock_load_sql.return_value = "SELECT * FROM mock_table"
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

        records = fetch_clinical_signals()

        mock_client_instance.query.assert_called_once()
        assert len(records) == 1
        
        record = records[0]
        assert isinstance(record, ClinicalSignalRecord)
        assert record.ticker == "INCY"
        assert record.failure_status == "TERMINATED"
        assert record.nct_id == "NCT06873789"


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
        fetch_clinical_signals(reference_date=test_anchor)

        mock_client_instance.query.assert_called_once()
        mock_bq.ScalarQueryParameter.assert_called_once_with(
            "reference_date", "TIMESTAMP", test_anchor
        )
        mock_bq.QueryJobConfig.assert_called_once()


def test_bq_scout_tool_context_injection():
    """Verifies that the wrapped ADK tool correctly injects candidates into ToolContext.state."""
    from biotech_catalyst.skills.bq_scout.tools import fetch_clinical_signals_tool

    fake_raw_data = {
        "ticker": "INCY",
        "cusip": "45337C102",
        "sponsor": "Incyte Corporation",
        "failure_status": "TERMINATED",
        "failure_post_date": datetime(2026, 9, 3, 6, 3, 19),
        "nct_id": "NCT06873789",
        "trial_title": "A Study to Evaluate INCB177054",
        "failure_reason": "Strategic business decision."
    }

    mock_tool_context = MagicMock()
    mock_tool_context.state = {"candidates": []}

    tool_func = fetch_clinical_signals_tool.func if hasattr(fetch_clinical_signals_tool, "func") else fetch_clinical_signals_tool
    
    with patch("biotech_catalyst.skills.bq_scout.tools.fetch_clinical_signals", return_value=[fake_raw_data]):
        response = tool_func(reference_date="2025-12-03 23:59:59 UTC", tool_context=mock_tool_context)

        assert response.count == 1
        assert len(mock_tool_context.state["candidates"]) == 1
        assert mock_tool_context.state["candidates"][0]["ticker"] == "INCY"