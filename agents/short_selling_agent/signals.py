import json
import os
import google.generativeai as genai

# Import your tools and state
from short_selling_agent.state import CURRENT_RUN_STATE
from short_selling_agent.prompts import QUANT_COORDINATOR_INSTRUCTIONS
from short_selling_agent.stage_tools import (
    tool_fetch_bq_candidates,
    tool_stage_news,
    tool_stage_insiders,
    tool_read_full_dossier
)

# Configure Gemini directly (make sure GEMINI_API_KEY is in your environment)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY", os.environ.get("GOOGLE_API_KEY")))
# Using 1.5 Pro to match your Lead Quant Trader
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

AGENT_4_INSTRUCTIONS = QUANT_COORDINATOR_INSTRUCTIONS

def generate_all_signals():
    all_signals = []

    for test_date in DATES_TO_TEST:
        print(f"\n⚙️  Processing pipeline for {test_date}...")
        
        # 1. Reset State
        CURRENT_RUN_STATE.reset()
        
        # 2. Run Step 1 (BigQuery Candidates) in pure Python
        tool_fetch_bq_candidates(as_of_date=test_date, limit=3)
        tickers = [loser.ticker for loser in CURRENT_RUN_STATE.dossier.market_losers]
        
        if not tickers:
            print(f"   -> No losers found for {test_date}. Skipping.")
            continue
            
        print(f"   -> Found candidates: {tickers}")
        
        # 3. Run Step 2 & 3 (News and Insiders) in pure Python
        for ticker in tickers:
            tool_stage_news(ticker, as_of_date=test_date)
            tool_stage_insiders(ticker, as_of_date=test_date)
            
        # 4. Run Step 4 (Build Dossier)
        dossier_json = tool_read_full_dossier()
        
        # 5. Ask Gemini (Lead Quant Trader) for the verdict
        print(f"   -> Asking Lead Quant Trader for final verdict...")
        prompt = f"{AGENT_4_INSTRUCTIONS}\n\nHere is the Dossier:\n{dossier_json}"
        
        try:
            response = model.generate_content(prompt)
            print(f'--------- RESPONSE IS \n{response.text}\n---------')
            clean_output = response.text.replace("```json", "").replace("```", "").strip()
            
            decisions = json.loads(clean_output).get("final_decisions", [])
            
            for dec in decisions:
                if dec.get("action") == "SHORT":
                    print(f"      🚨 SIGNAL: SHORT {dec['ticker']} (Score: {dec.get('conviction_score')})")
                    all_signals.append({
                        "date": test_date,
                        "ticker": dec["ticker"],
                        "conviction_score": dec.get("conviction_score"),
                        "reasoning": dec.get("reasoning")
                    })
                else:
                    print(f"      🛡️ SIGNAL: AVOID {dec['ticker']}")
                    
        except Exception as e:
            print(f"⚠️ Error generating LLM response for {test_date}: {e}")

    # Save to file
    with open("signals.json", "w") as f:
        json.dump(all_signals, f, indent=4)
        
    print(f"\n✅ Finished! Saved {len(all_signals)} short signals to signals.json")

if __name__ == "__main__":
    generate_all_signals()