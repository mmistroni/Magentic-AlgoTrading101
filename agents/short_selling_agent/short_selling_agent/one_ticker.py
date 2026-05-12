# test_one_ticker.py
"""
Test: Run the full pipeline on one ticker, one historical date.
Verifies your agent data flow is working before full backtest.
"""

import os
import json
from pprint import pprint

# -----------------------------
# CONFIG
# -----------------------------
FMP_API_KEY = os.getenv('FMP_API_KEY')
GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

# Check env vars
assert FMP_API_KEY, "❌ FMP_API_KEY not set. Run: export FMP_API_KEY=your_key"
assert GEMINI_API_KEY, "❌ GEMINI_API_KEY not set. Run: export GEMINI_API_KEY=your_key"

TEST_TICKER = "GME"
TEST_DATE = "2023-09-11"

print(f"\n🧪 Starting test: {TEST_TICKER} on {TEST_DATE}")
print("🚀 Testing full data pipeline: FMP → Quant → Dossier → Print\n")

# -----------------------------
# IMPORTS (After env check)
# -----------------------------
from short_selling_agent.state import CURRENT_RUN_STATE
from short_selling_agent.stage_tools import (
    tool_fetch_bq_candidates,
    tool_stage_news,
    tool_stage_insiders,
    tool_stage_quant_data,
    tool_read_full_dossier
)

# -----------------------------
# STEP 1: Reset state
# -----------------------------
print("1. Resetting CURRENT_RUN_STATE...")
CURRENT_RUN_STATE.reset()

# -----------------------------
# STEP 2: Simulate — add GME as a market loser
# (in case it wasn't in BQ that day)
# -----------------------------
print(f"2. Simulating: Add {TEST_TICKER} as market loser")
from short_selling_agent.schemas import MarketLoser
CURRENT_RUN_STATE.dossier.market_losers.append(
    MarketLoser(ticker=TEST_TICKER, price=18.75, change_pct=-14.2)
)

# -----------------------------
# STEP 3: Stage all data
# -----------------------------
print(f"3. Staging news for {TEST_TICKER}...")
tool_stage_news(TEST_TICKER, as_of_date=TEST_DATE)

print(f"4. Staging insiders for {TEST_TICKER}...")
tool_stage_insiders(TEST_TICKER, as_of_date=TEST_DATE)

print(f"5. Staging quant data for {TEST_TICKER}... (RSI, ADX, short %)")
tool_stage_quant_data(TEST_TICKER, as_of_date=TEST_DATE)

# -----------------------------
# STEP 4: Read full dossier (what agent sees)
# -----------------------------
print("\n🔐 Final Dossier (Agent Input):")
dossier_json = tool_read_full_dossier()
dossier_dict = json.loads(dossier_json)

# Pretty print key parts
print("\n📌 Market Losers:")
pprint(dossier_dict['market_losers'])

if dossier_dict['news_reports']:
    print("\n📰 News Reports (first article):")
    print({k: v for k, v in dossier_dict['news_reports'][0].items() if k != 'articles'})
    print(f"   Articles: {len(dossier_dict['news_reports'][0]['articles'])} news items")

if dossier_dict['insider_reports']:
    print("\n💼 Insider Reports:")
    print({k: v for k, v in dossier_dict['insider_reports'][0].items() if k != 'significant_sales'})
    print(f"   # Sales: {len(dossier_dict['insider_reports'][0]['significant_sales'])}")

if dossier_dict['quant_reports']:
    print("\n📊 Quantitative Signals:")
    quant = dossier_dict['quant_reports'][0]
    print(f"   Price: {quant['latest_price']}")
    print(f"   Below SMA200: {quant['price_below_sma200']}")
    print(f"   RSI(14): {quant['rsi_14']}")
    print(f"   ADX(14): {quant['adx_14']}")
    print(f"   Short Interest %: {quant['short_interest_pct']}")
    print(f"   Short-Squeeze Risk: {quant['short_squeeze_risk']}")
    print(f"   Earnings Miss: {quant['recent_earnings_miss']}")

# Also save to file
with open("test_one_ticker_dossier.json", "w") as f:
    json.dump(dossier_dict, f, indent=2)

print(f"\n✅ Test complete.")
print(f"📁 Full dossier saved to: test_one_ticker_dossier.json")
print(f"💡 Next: Open this file and verify quant data exists.")
print(f"✅ If RSI, ADX, short % are present → your agent will see them.")