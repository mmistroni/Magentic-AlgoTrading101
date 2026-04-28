##  Agent on Cloud Run - 
Short selling agent using outlier llm

here is how to run the backtest
(.venv) vscode@codespaces-6656da:/workspaces/Magentic-AlgoTrading101/agents/short_selling_agent$ python -m tests.integration.backtest_one_day --date 2025-06-01

-- prompts ---

Run the short-selling pipeline [for YYYY-MM-DD].”

• Run the short-selling pipeline for 2023-06-01.
• Run the short-selling pipeline.


User prompt
“Run the short-selling pipeline for 2023-06-01.”
(If you want “today,” you can literally write “Run the short-selling pipeline for 2026-04-28.”)

Updated agent definitions
– Each agent will simply re-parse that same date from the conversation history and forward it to its tool.
– You always supply a date, so no need for a fallback.