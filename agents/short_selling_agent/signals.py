# signal_generator.py

import json
import os
import google.generativeai as genai

# Import your tools and state
from short_selling_agent.state import CURRENT_RUN_STATE
from short_selling_agent.stage_tools import (
    tool_fetch_bq_candidates,
    tool_stage_news,
    tool_stage_insiders,
    tool_stage_quant_data,              # ✅ Added
    tool_read_full_dossier
)

# Configure Gemini
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY")))
model = genai.GenerativeModel("gemini-1.5-flash")  # ✅ Use stable model version

# -----------------------------
# HISTORICAL DATES (FIX: REMOVE FUTURE DATES)
# -----------------------------
# ❌ Old: future fake dates
# ✅ New: real, historical backtest range
HISTORICAL_DATES = [
    "2023-09-11", "2023-09-18", "2023-09-25",
    "2023-10-02", "2023-10-09", "2023-10-16",
    "2023-10-23", "2023-10-30", "2023-11-06",
    "2023-11-13", "2023-11-20", "2023-11-27",
    "2023-12-04", "2023-12-11", "2023-12-18"
]

AGENT_INSTRUCTIONS = """
You are the Lead Quant Trader. I am providing you with a JSON dossier containing:

- Market Losers (biggest daily downers)
- Latest News Headlines
- Form 4 Insider Sales
- Quantitative Technicals (RSI, ADX, SMA, Short Interest) ✅

Every stock in this list is already a major loser.

RULES:

• RULE 1 (Short Triggers): Only SHORT if:
    A) There is devastating news AND the stock broke key support.
    B) Massive C-suite insider selling.
    C) An unexplained 20%+ collapse with no news → "pump and dump unwinding".

• RULE 2 (Short-Squeeze Veto – STRICT):
    → AVOID if short interest > 20% (high squeeze risk).
    → AVOID if free float < 15M shares.
    ✅ Always check these.

• RULE 3 (Noise Filter): AVOID if:
    - The drop is < 10% AND no news
    - OR RSI > 60 → not bearish
    - OR price is above SMA200 → still in uptrend

• Use Quant Data:
    - RSI < 40 → supports bearish view
    - ADX > 25 → trend strength → supports breakout
    - Price below SMA200 → structural breakdown
    - Short Interest > 20% → VETO (critical)

For each ticker, output only this JSON format:
{
  "final_decisions": [
    {
      "ticker": "AAPL",
      "conviction_score": 8,  // 1–10
      "action": "SHORT",      // or "AVOID"
      "reasoning": "Explain using BOTH news and quantitative data"
    }
  ]
}
"""

def generate_all_signals():
    all_signals = []
    print("🚀 Starting historical short-signal generation...")

    for test_date in HISTORICAL_DATES:
        print(f"\n📅 Processing date: {test_date}")
        CURRENT_RUN_STATE.reset()  # ← Critical

        # Step 1: Get market losers
        tool_fetch_bq_candidates(as_of_date=test_date, limit=5)
        tickers = [loser.ticker for loser in CURRENT_RUN_STATE.dossier.market_losers]

        if not tickers:
            print(f"  ⚠️ No tickers for {test_date}")
            continue

        # Step 2: For each ticker → stage data
        for ticker in tickers:
            print(f"  → Processing: {ticker}")
            tool_stage_news(ticker, as_of_date=test_date)
            tool_stage_insiders(ticker, as_of_date=test_date)
            tool_stage_quant_data(ticker, as_of_date=test_date)  # ✅ ADDED

        # Step 3: Build dossier → send to Agent
        dossier_json = tool_read_full_dossier()
        prompt = f"{AGENT_INSTRUCTIONS}\n\nHere is the Dossier:\n{dossier_json}"

        try:
            response = model.generate_content(prompt)
            raw_text = response.text.strip()

            # Parse JSON safely
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}') + 1
            if start_idx == -1 or end_idx == 0:
                continue

            clean_json_str = raw_text[start_idx:end_idx]
            decisions_data = json.loads(clean_json_str)

            for decision in decisions_data.get("final_decisions", []):
                if decision.get("action") == "SHORT":
                    all_signals.append({
                        "date": test_date,
                        "ticker": decision["ticker"],
                        "conviction_score": decision["conviction_score"],
                        "reasoning": decision["reasoning"]
                    })

        except Exception as e:
            print(f"  ❌ Failure on {test_date}: {str(e)}")
            continue

        # Save continuously
        with open("signals.json", "w") as f:
            json.dump(all_signals, f, indent=4)

        print(f"  ✅ Done. Total shorts so far: {len(all_signals)}")

    print(f"\n✅ Backtest complete. {len(all_signals)} signals saved to 'signals.json'")


if __name__ == "__main__":
    generate_all_signals()