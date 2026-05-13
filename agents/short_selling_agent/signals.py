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
You are the Lead Quant Trader.

I'm providing a JSON dossier per ticker, including:
- Market Losers (biggest decliners)
- News Headlines
- Form 4 Insider Sales
- Quantitative Signals (RSI, ADX, SMA, Short Interest)

⚠️ Every stock is already a major loser — your job is to **filter, not chase**.

Apply the following **quantitative risk framework**:

• RULE 1: SHORT only with *strong technical confirmation*:
    A) Devastating negative news + RSI(14) < 40 → bearish momentum
    B) C-suite insider dumping + price below SMA200 → structural break
    C) 20%+ collapse with no news → "pump and dump" unwinding (confirm RSI < 40)

• RULE 2: AVOID immediately — short-squeeze risk:
    → AVOID if short interest > 20%
    → AVOID if free float < 15M shares
    ⛔ Never override this rule, even with news.

• RULE 3: AVOID if noise:
    → Drop < 10% AND no news → noise
    → RSI > 60 → not bearish
    → Price above SMA200 → still in uptrend → exit

• RULE 4: Use Quant Data First:
    - RSI < 40 → required for all SHORTs
    - ADX > 25 → strong trend → supports breakout
    - Price below SMA200 → structural breakdown → confirms short
    - Short Interest > 20% → VETO — do NOT short
    ✅ These signals are truth — news is lagging.

For each ticker, output ONLY valid JSON:
{
  "final_decisions": [
    {
      "ticker": "GME",
      "conviction_score": 9,
      "action": "SHORT",  // or "AVOID"
      "reasoning": "Explain using BOTH news and quantitative signals. Cite numeric values: 'RSI(34.5), price below SMA200 (18.0 < 22.5), short interest (23.1%) → avoid'"
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