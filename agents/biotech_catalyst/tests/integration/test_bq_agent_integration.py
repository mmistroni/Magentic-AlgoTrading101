import importlib.util
import os
import pytest
from unittest.mock import patch, MagicMock

# Dynamically load the tool script safely via file path (bypasses hyphen lookup issues completely)
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

from biotech_catalyst.catalyst_agents import bq_scout_agent


@pytest.mark.integration
def test_bq_scout_agent_tool_invocation():
    """Near-integration test verifying that the agent tool executes properly with mocked BigQuery."""
    
    # Patch directly on the loaded module object (no string dot-notation lookup over hyphenated folders)
    with patch.object(bq_scout_tools, "bigquery") as mock_bq, \
         patch.object(bq_scout_tools, "load_sql_query") as mock_load_sql:
        
        mock_load_sql.return_value = "SELECT * FROM mock_table"
        mock_client_instance = mock_bq.Client.return_value
        mock_query_job = MagicMock()
        mock_query_job.result.return_value = []
        mock_client_instance.query.return_value = mock_query_job

        # Execute tool invocation without positional arguments (matching the updated signature)
        result = fetch_clinical_signals()

        # Assertions
        mock_client_instance.query.assert_called_once()
        assert result == []