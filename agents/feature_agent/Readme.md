##  Agent on Cloud Run - 
Cloud run agent to interpert form 13f##
Brainstormed using Bard

Sample prompt:
"Run the backtest for the quarter ending 2024-12-31. Provide the results in a table showing the Ticker, Elite Count, Entry Price, and 6-month Return."

# Better Prompt
Prompt:

The Final Test: 2023 Elite Class Audit
Prompt:
"Perform a High-Conviction Sniper Audit for the 2023 Elite Class.

Workflow:

Use fetch_consensus_holdings_tool for 2023-12-31.

Apply the Adaptive Sniper Logic:

Start with strict_mode=True (Iterations 1-3).

If < 15 tickers pass, pivot to strict_mode=False (Iterations 4-5).

The Slicing: Sort by Manager Count and take the Top 15.

The Audit: Calculate the 180-day ROI starting from the disclosure date (2024-02-14).

Reporting: In the Executive Summary, explicitly state if you had to trigger 'Relaxed Momentum' mode. This is the final verification of the 'Adaptive' amendment."


TODO:Agent still needs to be deployed


Every time you launch a new Codespace, run the following to authenticate:
```bash
echo "$GCP_SA_KEY" > /tmp/gcp_key.json && export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_key.json


====== 20260618 - Full sec 13 download. we try these prompts

Prompt 1: The 2024 Historical Backtest Audit

Use this prompt to test the BACKTEST data pipeline, the 45-day disclosure lag calculation, and the 180-day ROI tool chaining logic.

Perform a High-Conviction Sniper Audit for the target date "2024-12-31".

Execute the workflow strictly in order:
1. Detect the mode based on the target date (set MODE = BACKTEST).
2. Run Adaptive Discovery loops (Iterations 1-5) to discover consensus tickers. Start with strict_mode=True; if you have fewer than 15 tickers, pivot to strict_mode=False.
3. Slice the Top 15 holdings sorted by Manager Count.
4. Call get_forward_return_tool with sanitized tickers (no parenthetical metadata) to audit the 180-day performance starting 45 days after target_date (2025-02-14).
5. Apply Phase 5 Critique Filters to categorize underperformers into Structural Losers (Below SMA200) vs Laggards (Above SMA200).

Present the final output exactly in Table 1 (Original Selection), Table 2 (Critique Filter Analysis), and the complete Executive Summary with Refined ROI metrics.





Prompt 2: Live Execution Portfolio Deployment - to investigate

Use this prompt to run the live risk-mitigation pipeline. This triggers LIVE mode, bypasses future performance returns, and analyzes current technical trend structures to proactively shield capital.

Initialize a live-execution strategy audit for the target date "2026-03-31".

Execute the workflow strictly in order:
1. Detect the mode based on the target date (set MODE = LIVE).
2. Execute the discovery loops to gather current Elite consensus holdings, automatically paginating with fetch_consensus_holdings_tool.
3. Perform current technical checks using get_technical_metrics_tool.
4. Slice the Top 15 candidates by Manager Count.
5. Apply the Proactive Critique Filter: immediately CUT any tickers showing "SMA200:DOWN" or "SMA50:DOWN" to protect our downside capital risk today.

Format the output strictly as specified: Table 1 (Trend Status), Table 2 (Proactive Cuts), and the Executive Summary recommending the finalized execution tickers.


Prompt 3: Prompt 2: The 2022 Historical Backtest Aud


Perform a High-Conviction Sniper Audit for the target date "2022-06-30".

Execute the workflow strictly in order:
1. Detect the mode based on the target date (set MODE = BACKTEST).
2. Run Adaptive Discovery loops (Iterations 1-5) to discover consensus tickers. Start with strict_mode=True; if you have fewer than 15 tickers, pivot to strict_mode=False.
3. Slice the Top 15 holdings sorted by Manager Count.
4. Call get_forward_return_tool with sanitized tickers (no parenthetical metadata) to audit the 180-day performance starting 45 days after target_date (2025-02-14).
5. Apply Phase 5 Critique Filters to categorize underperformers into Structural Losers (Below SMA200) vs Laggards (Above SMA200).

Present the final output exactly in Table 1 (Original Selection), Table 2 (Critique Filter Analysis), and the complete Executive Summary with Refined ROI metrics.

able 1: Original Top 15 Selection (Backtest)
Ticker	Elite Count	Entry Price	6-mo Return
AAPL	865	$147.10	9.64%
V	146	$174.06	27.88%
XOM	119	$78.45	33.74%
UNH	114	$478.56	-0.26%
MA	93	$283.75	25.97%
COST	93	$466.49	2.17%
RSP	69	$123.20	10.02%
XLV	68	$116.35	8.41%
TMO	55	$511.94	12.11%
SPYV	53	$32.92	15.03%
MELI	48	$865.24	44.47%
PEP	46	$148.91	10.29%
SCHV	45	$18.54	10.04%
XLI	41	$80.76	15.51%
UNP	38	$185.03	-2.53%
Table 2: Critique Filter Analysis
Ticker	Verdict (Cut/Hold)	Technical Reason
AAPL	HOLD (Performer)	Trading above 200-day SMA
V	HOLD (Performer)	Trading above 200-day SMA
XOM	HOLD (Performer)	Trading above 200-day SMA
UNH	Laggard (HOLD)	Trading above 200-day SMA, but negative return
MA	HOLD (Performer)	Trading above 200-day SMA
COST	HOLD (Performer)	Trading above 200-day SMA
RSP	HOLD (Performer)	Trading above 200-day SMA
XLV	HOLD (Performer)	Trading above 200-day SMA
TMO	HOLD (Performer)	Trading above 200-day SMA
SPYV	HOLD (Performer)	Trading above 200-day SMA
MELI	HOLD (Performer)	Trading above 200-day SMA
PEP	HOLD (Performer)	Trading above 200-day SMA
SCHV	HOLD (Performer)	Trading above 200-day SMA
XLI	HOLD (Performer)	Trading above 200-day SMA
UNP	Laggard (HOLD)	Trading above 200-day SMA, but negative return
Executive Summary:
ROI / Win Rate (Original): Average ROI: 15.49% | Win Rate: 86.67%
Refined ROI: 15.49%
Refined List for Execution: Not applicable for backtest.
Strategy Status: Relaxed Mode was triggered
Recovery Verdict: For UNH and UNP (Laggards), the advice is to hold.


Prompt 3 : The 2023 Historical Backtest Aud


Perform a High-Conviction Sniper Audit for the target date "2023-03-31".

Execute the workflow strictly in order:
1. Detect the mode based on the target date (set MODE = BACKTEST).
2. Run Adaptive Discovery loops (Iterations 1-5) to discover consensus tickers. Start with strict_mode=True; if you have fewer than 15 tickers, pivot to strict_mode=False.
3. Slice the Top 15 holdings sorted by Manager Count.
4. Dynamically calculate the Entry Date as exactly 45 days after "2023-03-31". Call get_forward_return_tool with sanitized tickers to audit the 180-day performance starting on that calculated Entry Date.
5. Apply Phase 5 Critique Filters to categorize underperformers into Structural Losers (Below SMA200) vs Laggards (Above SMA200).

Present the final output exactly in Table 1 (Original Selection), Table 2 (Critique Filter Analysis), and the complete Executive Summary with Refined ROI metrics.




Prompt 3 : The 2023 Historical Backtest Aud


Perform a High-Conviction Sniper Audit for the target date "2025-06-30".

Execute the workflow strictly in order:
1. Detect the mode based on the target date (set MODE = BACKTEST).
2. Run Adaptive Discovery loops (Iterations 1-5) to discover consensus tickers. Start with strict_mode=True; if you have fewer than 15 tickers, pivot to strict_mode=False.
3. Slice the Top 15 holdings sorted by Manager Count.
4. Dynamically calculate the Entry Date as exactly 45 days after "2025-06-30". Call get_forward_return_tool with sanitized tickers to audit the 180-day performance starting on that calculated Entry Date.
5. Apply Phase 5 Critique Filters to categorize underperformers into Structural Losers (Below SMA200) vs Laggards (Above SMA200).

Present the final output exactly in Table 1 (Original Selection), Table 2 (Critique Filter Analysis), and the complete Executive Summary with Refined ROI metrics.

















================= TEMPLATe  ========
Perform a High-Conviction Sniper Audit for the target date "{{TARGET_DATE}}".

Execute the workflow strictly in order:
1. Detect the mode based on the target date (set MODE = BACKTEST).
2. Run Adaptive Discovery loops (Iterations 1-5) to discover consensus tickers. Start with strict_mode=True; if you have fewer than 15 tickers, pivot to strict_mode=False.
3. Slice the Top 15 holdings sorted by Manager Count.
4. Dynamically calculate the Entry Date as exactly 45 days after "{{TARGET_DATE}}". Call get_forward_return_tool with sanitized tickers to audit the 180-day performance starting on that calculated Entry Date.
5. Apply Phase 5 Critique Filters to categorize underperformers into Structural Losers (Below SMA200) vs Laggards (Above SMA200).

Present the final output exactly in Table 1 (Original Selection), Table 2 (Critique Filter Analysis), and the complete Executive Summary with Refined ROI metrics.