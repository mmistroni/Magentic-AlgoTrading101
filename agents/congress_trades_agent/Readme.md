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
Current Analysis Date: 01 September 2024

Please execute the Congress Alpha Strategy:
1. First, research the political and legislative atmosphere for the month surrounding 01 September 2024.
2. Then, use that context to validate high-conviction Congress trades for the same date.
"""

# TEst Dates

Recommended Backtesting Dates
Since your data spans November 2024 to February 2026, and your SQL query uses a 90-day lookback, you cannot effectively backtest November 2024 (because the lookback period would be empty).

You should test these specific "Quarterly" checkpoints to see how the strategy evolves:

1. The "Ramp-Up" Date: 2025-02-01

Why: This is the first date where you have a full 90 days of history (Nov, Dec, Jan) populated in your database. The signals here will be the first "fully valid" ones.
2. The "Mid-Year" Check: 2025-06-01

Why: This captures the Spring/Summer legislative session trades.
3. The "Year-End" Check: 2025-11-01

Why: This gives you exactly one year of data. It captures end-of-year budget spending trades.
4. The "Final" Check: 2026-02-01

Why: This is the end of your dataset. It allows you to see if the strategy held up over the full 15-month period