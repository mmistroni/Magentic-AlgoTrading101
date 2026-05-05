import json
import os
import google.generativeai as genai

# Import your tools and state
from short_selling_agent.state import CURRENT_RUN_STATE
from short_selling_agent.stage_tools import (
    tool_fetch_bq_candidates,
    tool_stage_news,
    tool_stage_insiders,
    tool_read_full_dossier
)

# Configure Gemini directly
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY")))
model = genai.GenerativeModel("gemini-2.5-flash")

DATES_TO_TEST = [
    "2026-03-26", "2026-03-27", "2026-03-30", "2026-03-31",
    "2026-04-01", "2026-04-02", "2026-04-03", "2026-04-06",
    "2026-04-07", "2026-04-08", "2026-04-09", "2026-04-10",
    "2026-04-13", "2026-04-14", "2026-04-15", "2026-04-16",
    "2026-04-17", "2026-04-20", "2026-04-21", "2026-04-23",
    "2026-04-24", "2026-04-26", "2026-04-27", "2026-04-28",
    "2026-04-29", "2026-04-30", "2026-05-01", "2026-05-04"
]

AGENT_4_INSTRUCTIONS = """
You are the Lead Quant Trader. I am providing you with a JSON dossier containing Market Data, News, and Form 4 Insider Sales for a specific date.
Keep in mind: Every stock in this dossier is ALREADY one of the biggest daily losers in the market (gapping down significantly).

Synthesize this data using the following Balanced Risk Management rules:

• RULE 1 (The Short Triggers): You should output SHORT if the stock is suffering a massive drop AND you see either:
    A) Devastating negative news (earnings miss, dilution, FDA rejection).
    B) Massive C-Suite insider dumping in the recent months (showing management abandoned ship).
    C) An unexplained collapse (e.g., dropping 20%+) with NO news, which often signals a "pump and dump" unwinding.

• RULE 2 (The Short-Squeeze Veto - STRICT): Output AVOID immediately, no matter how bad the news is, if the stock is a severe short-squeeze trap. This means:
    - Free Float is very low (e.g., under 15 million shares), OR
    - Short Interest is dangerously high (e.g., over 20%).

• RULE 3 (The Noise Filter): Output AVOID if the stock is only down a small amount (e.g., less than 10%) with no bad news and no insider selling, as this is just normal market noise.

For each ticker, output a JSON object exactly like this (do not output any markdown formatting, ONLY valid JSON):
{
  "final_decisions": [
    { "ticker": "AAPL", "conviction_score": 8, "action": "SHORT", "reasoning": "Explain why..." }
  ]
}
"""

def generate_all_signals():
    all_signals = []
    print("🚀 Generating signals. This will run quietly to maximize speed...")

    for test_date in DATES_TO_TEST:
        CURRENT_RUN_STATE.reset()
        
        tool_fetch_bq_candidates(as_of_date=test_date, limit=3)
        tickers = [loser.ticker for loser in CURRENT_RUN_STATE.dossier.market_losers]
        
        if not tickers:
            print(f"[{test_date}] No data. Skipped.")
            continue
            
        for ticker in tickers:
            tool_stage_news(ticker, as_of_date=test_date)
            tool_stage_insiders(ticker, as_of_date=test_date)
            
        dossier_json = tool_read_full_dossier()
        prompt = f"{AGENT_4_INSTRUCTIONS}\n\nHere is the Dossier:\n{dossier_json}"
        
        try:
            response = model.generate_content(prompt)
            raw_text = response.text
            start_idx = raw_text.find('{')
            end_idx = raw_text.rfind('}')
            
            if start_idx != -1 and end_idx != -1:
                clean_json_str = raw_text[start_idx:end_idx+1]
                decisions = json.loads(clean_json_str).get("final_decisions", [])
                
                for dec in decisions:
                    if dec.get("action") == "SHORT":
                        all_signals.append({
                            "date": test_date,
                            "ticker": dec.get("ticker", "UNKNOWN"),
                            "conviction_score": dec.get("conviction_score", 0),
                            "reasoning": dec.get("reasoning", "")
                        })
        except Exception:
            pass # Fails silently to keep speed up

        # Save quietly in the background
        with open("signals.json", "w") as f:
            json.dump(all_signals, f, indent=4)
            
        print(f"[{test_date}] Processed. Total shorts found so far: {len(all_signals)}")

    print(f"\n✅ Finished! Saved {len(all_signals)} total short signals to signals.json")

if __name__ == "__main__":
    generate_all_signals()