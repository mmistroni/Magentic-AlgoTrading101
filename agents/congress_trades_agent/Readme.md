##  Agent on Cloud Run - 
Cloud run agent to interpert congress trades
Brainstorme dusing Gemini 3 pro on outlier

Todo: agent needs to be tested locally


Every time you launch a new Codespace, run the following to authenticate:
```bash
echo "$GCP_SA_KEY" > /tmp/gcp_key.json && export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_key.json

Sample prompt

# The Prompt string
user_prompt = f"""
Current Analysis Date: 2026-02-01

Please execute the Congress Alpha Strategy:
1. First, research the political and legislative atmosphere for the month surrounding 2026-02-01.
2. Then, use that context to validate high-conviction Congress trades for the same date.
"""

# TEst Dates

Recommended Backtesting Dates
Since your data spans November 2024 to February 2026, and your SQL query uses a 90-day lookback, you cannot effectively backtest November 2024 (because the lookback period would be empty).

You should test these specific "Quarterly" checkpoints to see how the strategy evolves:

1. The "Ramp-Up" Date: 2025-02-01

Why: This is the first date where you have a full 90 days of history (Nov, Dec, Jan) populated in your database. The signals here will be the first "fully valid" ones.

[
  {
    "ticker": "HD",
    "action": "PASS",
    "confidence": 9,
    "risk_rating": "High",
    "reason": "Thesis: Infrastructure/Construction mentioned as a potential tailwind, but not a direct context play for Home Improvement retail. Fundamentals: P/E 25.91, Beta 1.09, Debt/Equity 544.586. Signal: Net Buy Activity 40. Verdict: Pass."
  },
  {
    "ticker": "JPM",
    "action": "BUY",
    "confidence": 8,
    "risk_rating": "Medium",
    "reason": "Thesis: Financials could see eased regulatory burdens under a Republican administration (one probable scenario). Fundamentals: P/E 13.77, Beta 1.05, Debt/Equity N/A (normal for financial sector). Signal: Net Buy Activity 39. Verdict: Buy."
  },
  {
    "ticker": "COR",
    "action": "PASS",
    "confidence": 9,
    "risk_rating": "High",
    "reason": "Thesis: Healthcare sector has mixed political outlook; potential for drug pricing headwinds under some scenarios. No clear direct context play. Fundamentals: P/E 18.38, Beta 0.69, Debt/Equity 472.584. Signal: Net Buy Activity 31. Verdict: Pass."
  },
  {
    "ticker": "FCFS",
    "action": "BUY",
    "confidence": 8,
    "risk_rating": "Medium",
    "reason": "Thesis: Financials could see eased regulatory burdens under a Republican administration (one probable scenario). Fundamentals: P/E 14.8, Beta 0.48, Debt/Equity 112.821. Signal: Net Buy Activity 30. Verdict: Buy."
  }
]





2. The "Mid-Year" Check: 2025-06-01


[
  {
    "ticker": "MKL",
    "action": "BUY",
    "confidence": 7,
    "risk_rating": "Low",
    "reason": "Thesis: No direct political context support for Financial Services (Property & Casualty Insurance). Fundamentals: P/E 17.01, Beta 0.77 (low volatility), Debt/Equity 23.042 (healthy). Signal: Net Buy Score 30 (strong insider buying activity, qualifying as an 'Insider Play'). Verdict: Buy."
  },
  {
    "ticker": "NVT",
    "action": "BUY",
    "confidence": 8,
    "risk_rating": "Medium",
    "reason": "Thesis: Supply chain resilience initiatives and 'friend-shoring' directly support US-based manufacturing and industrial equipment, aligning with nVent Electric's sector. Fundamentals: P/E 23.31, Beta 1.31 (moderate volatility), Debt/Equity 41.815 (healthy). Signal: Net Buy Score 20 (moderate insider buying, strong enough when combined with context). Verdict: Buy."
  },
  {
    "ticker": "FLT",
    "action": "PASS",
    "confidence": 3,
    "risk_rating": "High",
    "reason": "Thesis: Unknown sector, thus cannot align with political context. Fundamentals: P/E 0, Beta 1.0, Debt/Equity null (missing critical fundamental data, indicating high risk). Signal: Net Buy Score 20. Verdict: Pass (due to lack of essential fundamental information for risk assessment)."
  },
  {
    "ticker": "JLL",
    "action": "PASS",
    "confidence": 8,
    "risk_rating": "High",
    "reason": "Thesis: Commercial Real Estate (CRE) faces significant headwinds from higher interest rates and continued valuation concerns, directly impacting Real Estate Services. This strong negative political context outweighs insider buying signals. Fundamentals: P/E 16.9, Beta 1.41 (moderate-high volatility), Debt/Equity 47.732 (healthy). Signal: Net Buy Score 20. Verdict: Pass."
  },
  {
    "ticker": "IBM",
    "action": "PASS",
    "confidence": 5,
    "risk_rating": "Medium",
    "reason": "Thesis: The Technology sector faces a mixed political context with potential regulatory scrutiny on one hand and strategic importance for supply chain resilience on the other; no direct strong supportive context to warrant a 'Context Play'. Fundamentals: P/E 16.5, Beta 0.9 (low volatility), Debt/Equity 167.8. Signal: Net Buy Score 17 (does not meet the 'net_buy_activity > 20' threshold for a strong 'Insider Play'). Verdict: Pass (lacks sufficiently strong signals or direct context support)."
  }
]


Why: This captures the Spring/Summer legislative session trades.
3. The "Year-End" Check: 2025-11-01
[
  {
    "ticker": "MSDA",
    "action": "PASS",
    "confidence": 0,
    "risk_rating": "High",
    "reason": "Thesis: Political context points to specific sectors with tailwinds like Defense, Semiconductors, Industrials, AI, and Cybersecurity. Fundamentals: Sector, P/E, Beta, and Debt-to-Equity are unknown. Signal: Net Buy Score is 28. Verdict: Pass, due to insufficient fundamental data for proper risk assessment and sector alignment."
  },
  {
    "ticker": "SMCY",
    "action": "PASS",
    "confidence": 0,
    "risk_rating": "High",
    "reason": "Thesis: Political context points to specific sectors with tailwinds like Defense, Semiconductors, Industrials, AI, and Cybersecurity. Fundamentals: Sector, P/E, Beta, and Debt-to-Equity are unknown. Signal: Net Buy Score is 25. Verdict: Pass, due to insufficient fundamental data for proper risk assessment and sector alignment."
  },
  {
    "ticker": "FIG",
    "action": "BUY",
    "confidence": 8,
    "risk_rating": "Medium",
    "reason": "Thesis: The political context highlights strong tailwinds for Technology, particularly in AI, advanced computing, and cybersecurity, driven by US-China strategic competition and initiatives like the 'American Economic Resilience & Security Act.' This directly supports the Software - Application sector. Fundamentals: P/E is 102.68, Beta is 1.0, Debt-to-Equity is 4.41 (healthy). Signal: Net Buy Score is 24. Verdict: Buy."
  },
  {
    "ticker": "HLMIX",
    "action": "PASS",
    "confidence": 0,
    "risk_rating": "High",
    "reason": "Thesis: Political context points to specific sectors with tailwinds like Defense, Semiconductors, Industrials, AI, and Cybersecurity. Fundamentals: Sector, P/E, Beta, and Debt-to-Equity are unknown. Signal: Net Buy Score is 24. Verdict: Pass, due to insufficient fundamental data for proper risk assessment and sector alignment."
  }
]

Why: This gives you exactly one year of data. It captures end-of-year budget spending trades.
4. The "Final" Check: 2026-02-01

Why: This is the end of your dataset. It allows you to see if the strategy held up over the full 15-month period

[
  {
    "ticker": "CSCO",
    "action": "BUY",
    "confidence": 9,
    "risk_rating": "Low",
    "reason": "Thesis: \"Cybersecurity Infrastructure Protection Bill\" and rising state-sponsored cyber threats drive demand for network security, aligning with Cisco's offerings. Fundamentals: P/E 19.27, Beta 0.86, Debt/Equity 63.228 (healthy). Signal: Net Buy Score 21. Verdict: Buy."
  },
  {
    "ticker": "TSM",
    "action": "BUY",
    "confidence": 8,
    "risk_rating": "Medium",
    "reason": "Thesis: \"Advanced Industries Competitiveness Act\" and geopolitical risks (China-Taiwan tensions) amplify urgency for supply chain independence in Semiconductors. Fundamentals: P/E 20.11, Beta 1.27, Debt/Equity 18.187 (very healthy). Signal: Net Buy Score 17. Verdict: Buy."
  },
  {
    "ticker": "TSCO",
    "action": "PASS",
    "confidence": 3,
    "risk_rating": "High",
    "reason": "Thesis: No direct political context support. Consumer Cyclical sector faces headwinds from sticky inflation and high interest rates. Fundamentals: P/E 22.45, Beta 0.73, Debt/Equity 230.228 (high for non-utility/financial). Signal: Net Buy Score 15 (low conviction). Verdict: Pass."
  },
  {
    "ticker": "DELL",
    "action": "PASS",
    "confidence": 2,
    "risk_rating": "High",
    "reason": "Thesis: Indirect political context, not a strong \"Context Play\". Fundamentals: P/E 10.95, Beta 1.1, Debt/Equity: Unknown (critical data missing). Signal: Net Buy Score 15. Verdict: Pass."
  },
  {
    "ticker": "CSWI",
    "action": "PASS",
    "confidence": 1,
    "risk_rating": "Very High",
    "reason": "Thesis: Unable to assess political context due to unknown sector/industry. Fundamentals: P/E 0, Beta 1.0, Debt/Equity: Unknown (critical data missing). Signal: Net Buy Score 15. Verdict: Pass."
  }
]