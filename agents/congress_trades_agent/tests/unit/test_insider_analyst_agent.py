from unittest.mock import patch

from google.adk.agents import LlmAgent, SequentialAgent

from congress_trades_agent.schemas import InsiderContextPayload
from congress_trades_agent.skills.insider_analyst import insider_analyst
from congress_trades_agent.skills.insider_analyst.tools import (
    fetch_form4_signals_tool,
    fetch_lobbying_signals_tool,
)


def test_agent_structure_and_hierarchy():
    """Verify sequential agent structure, sub-agent wiring, tools, and schema configuration."""
    assert isinstance(insider_analyst, SequentialAgent)
    assert insider_analyst.name == "InsiderAnalyst"
    assert len(insider_analyst.sub_agents) == 2

    worker = insider_analyst.sub_agents[0]
    formatter = insider_analyst.sub_agents[1]

    # Verify Worker Agent Configuration
    assert isinstance(worker, LlmAgent)
    assert worker.name == "InsiderAnalystWorker"
    assert worker.output_key == "insider_notes"
    assert len(worker.tools) == 2

    # Verify Formatter Agent Configuration
    assert isinstance(formatter, LlmAgent)
    assert formatter.name == "InsiderAnalystFormatter"
    assert formatter.output_key == "insider_context"
    assert formatter.output_schema == InsiderContextPayload


@patch("congress_trades_agent.skills.insider_analyst.tools.get_form4_data")
@patch("congress_trades_agent.skills.insider_analyst.tools.get_lobbying_data")
def test_mock_agent_tool_execution(mock_get_lobbying, mock_get_form4):
    """Test underlying tool responses consumed during agent workflow."""
    # 1. Setup Mock BigQuery Return Values
    mock_get_form4.return_value = [
        {
            "ticker": "NVDA",
            "issuer": "NVIDIA Corp",
            "net_buy_value": 1500000.0,
            "unique_buyers": 4,
            "is_c_suite_buy": True,
            "is_cluster_buy": True,
            "buy_count": 4,
            "sell_count": 0,
            "insider_activity_score": 85.0,
        }
    ]

    mock_get_lobbying.return_value = [
        {
            "ticker": "NVDA",
            "client_name": "NVIDIA Corp",
            "key_issues": "CPT, TAX, DEF",
            "current_spend": 2500000.0,
            "prior_spend": 1000000.0,
            "spend_growth_pct": 150.0,
        }
    ]

    # 2. Directly invoke tools as agent would call them
    form4_res = fetch_form4_signals_tool.func(
        analysis_date="2026-03-01", ticker="NVDA"
    )
    lobbying_res = fetch_lobbying_signals_tool.func(
        analysis_date="2026-03-01", ticker="NVDA"
    )

    # 3. Assert correct payload structure for Formatter consumption
    assert form4_res.signals[0].ticker == "NVDA"
    assert form4_res.signals[0].insider_activity_score == 85.0

    assert lobbying_res.signals[0].ticker == "NVDA"
    assert lobbying_res.signals[0].spend_growth_pct == 150.0