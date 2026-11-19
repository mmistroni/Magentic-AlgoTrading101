import importlib.util
import os
from pathlib import Path
from unittest.mock import MagicMock
import pytest


def _load_module(module_name: str, file_path: Path):
    spec = importlib.util.spec_from_file_location(module_name, file_path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SKILL_DIR = PROJECT_ROOT / "biotech_catalyst" / "skills" / "bq-scout"

agent_mod = _load_module("bq_scout_agent_live", SKILL_DIR / "agent.py")
tools_mod = _load_module("bq_scout_tools_live", SKILL_DIR / "tools.py")

LIVE_BQ_ENABLED = os.getenv("RUN_LIVE_BQ_TESTS") == "1"


@pytest.mark.integration
@pytest.mark.live_bq
@pytest.mark.skipif(not LIVE_BQ_ENABLED, reason="Set RUN_LIVE_BQ_TESTS=1 to run live BigQuery integration tests.")
@pytest.mark.parametrize(
    ("reference_date", "expected_ticker", "expected_nct_id", "min_expected"),
    [
        ("2026-09-03 06:03:20 UTC", "INCY", "NCT06873789", 1),
        ("2026-11-13 06:02:18 UTC", "ELTX", "NCT06723171", 1),
    ],
)
def test_bq_scout_live_query_and_state_injection(
    reference_date: str,
    expected_ticker: str,
    expected_nct_id: str,
    min_expected: int,
):
    """Runs BQScout's tool against real BigQuery data for known historical reference dates."""
    assert agent_mod.bq_scout.name == "BQScout"
    assert tools_mod.fetch_clinical_signals_tool in agent_mod.bq_scout.tools

    tool_context = MagicMock()
    tool_context.state = {"candidates": []}

    wrapped_tool = tools_mod.fetch_clinical_signals_tool
    tool_fn = getattr(wrapped_tool, "func", wrapped_tool)

    result = tool_fn(reference_date=reference_date, tool_context=tool_context)

    assert result.error is None
    assert result.count >= min_expected
    assert len(tool_context.state["candidates"]) == result.count

    matches = [
        row for row in tool_context.state["candidates"]
        if row.get("ticker") == expected_ticker and row.get("nct_id") == expected_nct_id
    ]
    assert len(matches) >= 1


@pytest.mark.integration
@pytest.mark.live_bq
@pytest.mark.skipif(not LIVE_BQ_ENABLED, reason="Set RUN_LIVE_BQ_TESTS=1 to run live BigQuery integration tests.")
def test_bq_scout_live_empty_window():
    """Verifies clean zero-signal handling on a date window with no matching clinical failures."""
    tool_context = MagicMock()
    tool_context.state = {"candidates": []}

    wrapped_tool = tools_mod.fetch_clinical_signals_tool
    tool_fn = getattr(wrapped_tool, "func", wrapped_tool)

    result = tool_fn(reference_date="2026-08-15 00:00:00 UTC", tool_context=tool_context)

    assert result.error is None
    assert result.count == 0
    assert tool_context.state["candidates"] == []