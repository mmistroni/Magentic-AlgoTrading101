import importlib.util
from pathlib import Path
from unittest.mock import MagicMock
import pytest


def _load_tools_module():
    project_root = Path(__file__).resolve().parents[2]
    tools_path = project_root / "biotech_catalyst" / "skills" / "bq-scout" / "tools.py"
    spec = importlib.util.spec_from_file_location("bq_scout_tools_integration", tools_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


tools_mod = _load_tools_module()


def _invoke_tool(reference_date: str | None, state: dict | None = None):
    tool_context = MagicMock()
    tool_context.state = state if state is not None else {"candidates": []}

    wrapped_tool = tools_mod.fetch_clinical_signals_tool
    tool_fn = getattr(wrapped_tool, "func", wrapped_tool)
    response = tool_fn(reference_date=reference_date, tool_context=tool_context)
    return response, tool_context.state["candidates"]


@pytest.mark.integration
@pytest.mark.parametrize(
    ("reference_date", "expected_ticker", "expected_nct_id", "min_count"),
    [
        ("2026-09-03 06:03:20 UTC", "INCY", "NCT06873789", 1),
        ("2026-11-13 06:02:18 UTC", "ELTX", "NCT06723171", 1),
    ],
)
def test_bq_scout_returns_expected_candidates_for_reference_date(
    reference_date: str,
    expected_ticker: str,
    expected_nct_id: str,
    min_count: int,
):
    response, candidates = _invoke_tool(reference_date=reference_date)

    assert response.error is None
    assert response.count >= min_count
    assert len(candidates) == response.count

    matched = [
        item for item in candidates
        if item.get("ticker") == expected_ticker and item.get("nct_id") == expected_nct_id
    ]
    assert len(matched) >= 1
    assert matched[0].get("failure_status") in {"TERMINATED", "SUSPENDED", "WITHDRAWN"}


@pytest.mark.integration
def test_bq_scout_returns_empty_result_for_quiet_window():
    response, candidates = _invoke_tool(reference_date="2026-08-15 00:00:00 UTC")

    assert response.error is None
    assert response.count == 0
    assert candidates == []