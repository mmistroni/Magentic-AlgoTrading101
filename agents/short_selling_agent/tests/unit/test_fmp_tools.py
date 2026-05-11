# test_fmp_tools.py
import unittest
import os
import json
from datetime import datetime, timedelta

# Import your module
from fmp_tools import (
    get_historical_price_full,
    get_technical_indicators,
    get_short_interest,
    get_all_data_for_ticker
)

# -----------------------------
# CONFIG
# -----------------------------
FMP_API_KEY = os.getenv('FMP_API_KEY')
if not FMP_API_KEY:
    raise EnvironmentError("FMP_API_KEY not set. Use: export FMP_API_KEY=your_key")

SYMBOL = "AAPL"
AS_OF_DATE = "2023-08-15"  # A past date where data is stable


class TestFMPTools(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        print("\n🚀 Running FMP Tools Unit Tests\n")
        cls.as_of_dt = datetime.strptime(AS_OF_DATE, '%Y-%m-%d')

    def test_1_historical_price_full_date_constraint(self):
        """Ensure OHLCV data respects as_of_date"""
        data = get_historical_price_full(SYMBOL, as_of_date=AS_OF_DATE, lookback_days=30)

        self.assertGreater(len(data), 0, "Should return price data")

        # Check all dates <= as_of_date
        for item in data:
            item_date = datetime.strptime(item['date'], '%Y-%m-%d')
            self.assertLessEqual(item_date, self.as_of_dt, "No future data allowed")

    def test_2_rsi_computed_safely(self):
        """Test RSI is computed only on past data"""
        data = get_technical_indicators(
            symbol=SYMBOL,
            indicator_type="rsi",
            period_length=14,
            as_of_date=AS_OF_DATE,
            lookback_days=60
        )

        self.assertGreater(len(data), 10, "Should return RSI values")
        self.assertIn('date', data[0])
        self.assertIn('value', data[0])
        self.assertIsInstance(data[0]['value'], (float, type(None)), "RSI must be float or None")

        # All dates <= as_of_date
        for item in data:
            item_date = datetime.strptime(item['date'], '%Y-%m-%d')
            self.assertLessEqual(item_date, self.as_of_dt)

    def test_3_short_interest_before_as_of_date(self):
        """Short interest must be from <= as_of_date"""
        si = get_short_interest(SYMBOL, as_of_date=AS_OF_DATE)

        if si['shortDate'] is not None:
            si_dt = datetime.strptime(si['shortDate'], '%Y-%m-%d')
            self.assertLessEqual(si_dt, self.as_of_dt, "Short interest from future!")

    def test_4_technical_indicators_types(self):
        """Ensure all indicator types return consistent format"""
        for itype in ['sma', 'adx', 'bollinger_upper', 'bollinger_lower']:
            with self.subTest(indicator=itype):
                data = get_technical_indicators(SYMBOL, itype, as_of_date=AS_OF_DATE)
                if data:
                    self.assertIsInstance(data, list)
                    for item in data:
                        self.assertIn('date', item)
                        self.assertIn('value', item)
                        self.assertIsInstance(item['date'], str)
                        self.assertIsInstance(item['value'], (float, type(None)))

    def test_5_all_data_for_ticker_structure(self):
        """Test full agent context is correct"""
        data = get_all_data_for_ticker(SYMBOL, as_of_date=AS_OF_DATE, lookback_days=180)

        self.assertIsInstance(data, dict)
        self.assertEqual(data['symbol'], SYMBOL)
        self.assertEqual(data['as_of_date'], AS_OF_DATE)

        # Check structure
        self.assertIn('price', data)
        self.assertIn('indicators', data)
        self.assertIn('fundamentals', data)

        # Validate JSON serializable
        try:
            json.dumps(data, default=str)
        except Exception as e:
            self.fail(f"Data is not JSON serializable: {e}")

    def test_6_no_future_data_in_indicators(self):
        """Double-check no indicator returns a date after as_of_date"""
        for itype in ['rsi', 'adx', 'sma200']:
            data = get_technical_indicators(SYMBOL, itype, as_of_date=AS_OF_DATE)
            for item in data:
                item_dt = datetime.strptime(item['date'], '%Y-%m-%d')
                self.assertLessEqual(item_dt, self.as_of_dt, f"{itype} returned future data")

    def test_7_empty_cases_handled(self):
        """Should not crash on insufficient data"""
        # Test very short lookback
        data = get_technical_indicators(SYMBOL, "rsi", period_length=14, as_of_date="1980-01-01", lookback_days=5)
        self.assertIsInstance(data, list)
        self.assertEqual(len(data), 0, "Should return empty list, not error")


if __name__ == '__main__':
    unittest.main(verbosity=2)