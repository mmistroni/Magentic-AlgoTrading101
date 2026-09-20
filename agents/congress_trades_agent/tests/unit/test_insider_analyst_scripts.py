import unittest
from unittest.mock import MagicMock, patch
from pathlib import Path

from congress_trades_agent.skills.insider_analyst.scripts.insider_signals import get_form4_data
from congress_trades_agent.skills.insider_analyst.scripts.lobbying_signals import get_lobbying_data


class TestInsiderAnalystScripts(unittest.TestCase):

    @patch("congress_trades_agent.skills.insider_analyst.scripts.insider_signals.get_bq_client")
    def test_get_form4_data_invokes_bq_with_correct_params(self, mock_get_bq_client):
        # 1. Setup Mock BigQuery Client & Job
        mock_client = MagicMock()
        mock_get_bq_client.return_value = mock_client

        mock_query_job = MagicMock()
        # Mock row return
        mock_row = {
            "ticker": "NVDA",
            "issuer": "NVIDIA Corp",
            "net_buy_value": 500000.0,
            "unique_buyers": 2,
            "is_c_suite_buy": 1,
            "buy_count": 2,
            "sell_count": 0,
            "is_cluster_buy": False,
            "insider_activity_score": 45.0,
        }
        mock_query_job.result.return_value = [mock_row]
        mock_client.query.return_value = mock_query_job

        # 2. Execute Function
        test_date = "2026-03-01"
        test_ticker = "NVDA"
        results = get_form4_data(analysis_date=test_date, ticker=test_ticker, lookback_days=90)

        # 3. Assertions
        mock_client.query.assert_called_once()
        
        # Extract arguments passed to client.query(query, job_config=job_config)
        args, kwargs = mock_client.query.call_args
        sql_passed = args[0]
        job_config_passed = kwargs.get("job_config")

        # Verify SQL content loaded from reference file
        self.assertIn("form4_master", sql_passed)
        self.assertIn("aggregated_insider", sql_passed)

        # Verify BigQuery Parameter Bindings
        params = {p.name: p.value for p in job_config_passed.query_parameters}
        self.assertEqual(params["analysis_date"], "2026-03-01")
        self.assertEqual(params["ticker"], "NVDA")
        self.assertEqual(params["lookback_days"], 90)

        # Verify Output
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["ticker"], "NVDA")

    @patch("congress_trades_agent.skills.insider_analyst.scripts.lobbying_signals.get_bq_client")
    def test_get_lobbying_data_invokes_bq_with_correct_params(self, mock_get_bq_client):
        # 1. Setup Mock BigQuery Client & Job
        mock_client = MagicMock()
        mock_get_bq_client.return_value = mock_client

        mock_query_job = MagicMock()
        # Mock row return
        mock_row = {
            "ticker": "AAPL",
            "client_name": "Apple Inc.",
            "key_issues": "CPT, TAX, TRD",
            "current_spend": 1200000.0,
            "prior_spend": 800000.0,
            "spend_growth_pct": 50.0,
        }
        mock_query_job.result.return_value = [mock_row]
        mock_client.query.return_value = mock_query_job

        # 2. Execute Function
        test_date = "2026-03-01"
        results = get_lobbying_data(analysis_date=test_date, ticker=None, lookback_days=90)

        # 3. Assertions
        mock_client.query.assert_called_once()

        args, kwargs = mock_client.query.call_args
        sql_passed = args[0]
        job_config_passed = kwargs.get("job_config")

        # Verify SQL content loaded from reference file
        self.assertIn("lobbying_signals", sql_passed)
        self.assertIn("spend_growth_pct", sql_passed)

        # Verify BigQuery Parameter Bindings
        params = {p.name: p.value for p in job_config_passed.query_parameters}
        self.assertEqual(params["analysis_date"], "2026-03-01")
        self.assertIsNone(params["ticker"])
        self.assertEqual(params["lookback_days"], 90)

        # Verify Output
        self.assertEqual(len(results), 1)
        self.assertEqual(results[0]["spend_growth_pct"], 50.0)


if __name__ == "__main__":
    unittest.main()