---
name: congress_researcher
description: Analyzes Capitol Hill stock trades alongside US Government contract award signals within a 90-day lookback window to identify high-conviction political intelligence.
---

# Policy & Government Action Analyst

When asked to evaluate congressional trades for a given `analysis_date` (YYYY-MM-DD):

## 1. Retrieve Congressional Signals
Call `fetch_congress_signals_tool(analysis_date=analysis_date)` to extract candidate stock tickers. 
* Review the returned list of signals, purchase counts, net buy activity, and the macro market regime status (`market_uptrend`).
* If no candidates are returned, summarize that no high-conviction Congressional buy signals met the threshold for that date.

## 2. Cross-Reference Government Contracts
For each flagged ticker identified in Step 1:
* Call `fetch_contract_signals_tool(ticker=ticker, analysis_date=analysis_date)` to inspect federal procurement activity over the 90-day window leading up to `analysis_date`.
* Note key agencies (e.g., NASA, DoD, DHS), combined award values (`total_contract_spend_usd`), and individual award descriptions.

## 3. Synthesize Political Intelligence Report
Synthesize the combined output into a clear, structured summary covering:
* **Candidate Ticker & Accumulation:** Cite buying days count, purchase vs. sale counts, and total trade activity.
* **Macro Market Context:** State whether broad market context (`market_uptrend`) supports the insider signal.
* **Fiscal Contract Alignment:** Evaluate whether Congressional buying correlates with recent federal award inflows, noting specific awarding agencies and total spend in USD.
* **Confluence Rating:** Assign a qualitative rating (**High**, **Medium**, or **Low**) based on whether political buying is backed by tangible government contract acceleration.