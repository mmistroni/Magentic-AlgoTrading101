##  Agent on Cloud Run - 
Short selling agent using outlier llm
Sample prompt for results
Run the short-selling pipeline [for YYYY-MM-DD].
We got mail with flagged items for following dats
11/6
12/6
18/6
19/6
22/6
25/6


here is how to run the backtest
(.venv) vscode@codespaces-6656da:/workspaces/Magentic-AlgoTrading101/agents/short_selling_agent$ python -m tests.integration.backtest_one_day --date 2025-06-01

-- prompts ---

Run the short-selling pipeline [for YYYY-MM-DD].”

• Run the short-selling pipeline for 2025-05-12.
• Run the short-selling pipeline.


User prompt
“Run the short-selling pipeline for 2023-06-01.”
(If you want “today,” you can literally write “Run the short-selling pipeline for 2026-04-28.”)

Updated agent definitions
– Each agent will simply re-parse that same date from the conversation history and forward it to its tool.
– You always supply a date, so no need for a fallback.


--- test tickers
 one_tickers.py tests the flow
 signals.py run multiple signals
 run_backtest clculates pnl


