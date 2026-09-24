import importlib.util
from pathlib import Path
import pytest
from unittest.mock import patch, MagicMock
from datetime import datetime

# Dynamically load the tools module safely by file path (bypasses hyphenated folder limitation)
current_dir = Path(__file__).resolve().parent
tool_path = current_dir.parent.parent / "biotech_catalyst" / "skills" / "bq-scout" / "tools.py"

spec = importlib.util.spec_from_file_location("bq_scout_tools_module", tool_path)
bq_scout_tools_module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(bq_scout_tools_module)

# Extract the wrapped tool function from the dynamically loaded module
fetch_clinical_signals_tool = bq_scout_tools_module.fetch_clinical_signals_tool

from schemas import ClinicalSignalResponse


@patch("biotech_catalyst.skills.bq_scout.tools.fetch_clinical_signals") # Or patch directly on the module if needed
def test_fetch_clinical_signals_tool_success(mock_fetch):
    """Verifies that fetch_clinical_signals_tool correctly passes parameters, 
    populates shared state via ToolContext, and returns a valid response.
    """
    # 1. Arrange mock raw return data
    test_ref_date = "2025-12-03 23:59:59 UTC"
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
    
    mock_fetch.return_value = [fake_raw_data]

    # 2. Mock ADK ToolContext and its state dictionary
    mock_tool_context = MagicMock()
    mock_tool_context.state = {"candidates": []}

    # 3. Act: Execute the wrapped tool function (unwrapping the FunctionTool to test the inner logic function)
    # Note: FunctionTool wraps the callable under .func
    tool_func = fetch_clinical_signals_tool.func if hasattr(fetch_clinical_signals_tool, "func") else fetch_clinical_signals_tool
    response = tool_func(
        reference_date=test_ref_date, 
        tool_context=mock_tool_context
    )

    # 4. Assertions: Underlying function call
    mock_fetch.assert_called_once_with(test_ref_date)

    # 5. Assertions: Response structure
    assert isinstance(response, ClinicalSignalResponse)
    assert response.reference_date == test_ref_date
    assert response.count == 1
    assert response.error is None
    assert len(response.signals) == 1
    assert response.signals[0].ticker == "INCY"
    assert response.signals[0].failure_status == "TERMINATED"

    # 6. Assertions: Shared PipelineState mutation via ToolContext
    assert "candidates" in mock_tool_context.state
    candidates = mock_tool_context.state["candidates"]
    assert len(candidates) == 1
    assert candidates[0]["ticker"] == "INCY"
    assert candidates[0]["nct_id"] == "NCT06873789"


def test_fetch_clinical_signals_tool_error_handling():
    """Verifies graceful error catching and reporting when the underlying fetch fails."""
    test_ref_date = "2025-12-03 23:59:59 UTC"
    
    # Patch target path using dynamic reference or target patch string
    with patch("biotech_catalyst.skills.bq_scout.tools.fetch_clinical_signals") as mock_fetch:
        mock_fetch.side_effect = Exception("BigQuery connection timeout")

        mock_tool_context = MagicMock()
        mock_tool_context.state = {"candidates": []}

        tool_func = fetch_clinical_signals_tool.func if hasattr(fetch_clinical_signals_tool, "func") else fetch_clinical_signals_tool
        response = tool_func(
            reference_date=test_ref_date, 
            tool_context=mock_tool_context
        )

        assert isinstance(response, ClinicalSignalResponse)
        assert response.reference_date == test_ref_date
        assert response.error == "BigQuery connection timeout"
        assert response.count == 0