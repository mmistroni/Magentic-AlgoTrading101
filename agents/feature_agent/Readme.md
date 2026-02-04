##  Agent on Cloud Run - 
Cloud run agent to interpert form 13f##
Brainstormed using Bard

Sample prompt:
"Run the backtest for the quarter ending 2024-12-31. Provide the results in a table showing the Ticker, Elite Count, Entry Price, and 6-month Return."


TODO:Agent still needs to be deployed


Every time you launch a new Codespace, run the following to authenticate:
```bash
echo "$GCP_SA_KEY" > /tmp/gcp_key.json && export GOOGLE_APPLICATION_CREDENTIALS=/tmp/gcp_key.json