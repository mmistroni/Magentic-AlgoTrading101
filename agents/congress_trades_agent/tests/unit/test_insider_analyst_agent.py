import unittest
from unittest.mock import MagicMock, patch

from google.adk.agents import SequentialAgent, LlmAgent

from congress_trades_agent.skills.insider_analyst import insider_analyst
from congress_trades_agent.schemas import InsiderContextPayload


class TestInsiderAnalystIntegration(unittest.TestCase):

    def test_agent_structure_and_hierarchy(self):
        """Verify sequential agent structure, sub-agent wiring, tools, and schema configuration."""
        self.assertIsInstance(insider_analyst, SequentialAgent)
        self.assertEqual(insider_analyst.name, "InsiderAnalyst")
        self.assertEqual(len(insider_analyst.sub_agents), 2)

        worker = insider_analyst.sub_agents[0]
        formatter = insider_analyst.sub_agents[1]

        # Verify Worker Agent Configuration
        self.assertIsInstance(worker, LlmAgent)
        self.assertEqual(worker.name, "InsiderAnalystWorker")
        self.assertEqual(worker.output_key, "insider_notes")
        self.assertEqual(len(worker.tools), 2)

        # Verify Formatter Agent Configuration
        self.assertIsInstance(formatter, LlmAgent)
        self.assertEqual(formatter.name, "InsiderAnalystFormatter")
        self.assertEqual(formatter.output_key, "insider_context")
        self.assertEqual(formatter.output_schema, InsiderContextPayload)

    @patch("congress_trades_agent.skills.insider_analyst.tools.get_form4_data")
    @patch("congress_trades_agent.skills.insider_analyst.tools.get_lobbying_data")
    def test_mock_agent_tool_execution(self, mock_get_lobbying, mock_get_form4):
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
        from congress_trades_agent.skills.insider_analyst.tools import (
            fetch_form4_signals_tool,
            fetch_lobbying_signals_tool,
        )

        form4_res = fetch_form4_signals_tool.func(analysis_date="2026-03-01", ticker="NVDA")
        lobbying_res = fetch_lobbying_signals_tool.func(analysis_date="2026-03-01", ticker="NVDA")

        # 3. Assert correct payload structure for Formatter consumption
        self.assertEqual(form4_res.signals[0].ticker, "NVDA")
        self.assertEqual(form4_res.signals[0].insider_activity_score, 85.0)

        self.assertEqual(lobbying_res.signals[0].ticker, "NVDA")
        self.assertEqual(lobbying_res.signals[0].spend_growth_pct, 150.0)


if __name__ == "__main__":
    unittest.main()