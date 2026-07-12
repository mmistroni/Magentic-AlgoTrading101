##  Agent on Cloud Run - 
Short selling agent using outlier llm
This agent is supported by 3 differnet jobs
- a bq_ingestion job which stores daily market losers from FMP. this is for research purposes
- sec_sync a job which downloads from SEC Mappings from tickers to company names
- sync_catalyst.job which downloads data from clinical trials , to spot biotech
  catalysts.

(12/07) - job is in process of being converted following Skills API  



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

from short_selling_agent.stage_tools import (
    tool_fetch_bq_candidates, 
    tool_stage_news, 
    tool_stage_insiders, 
    tool_read_full_dossier
)

from .tools import (
    get_fmp_news,



===   Tools
BQ_INGESTION_AGENT = 
stage_tools.tool_fetch_bq_candidates,
          |__ tools.get_bq_short_candidates,
    

# ---------------------------------------------------------
# AGENT 2: News Analyst
# ---------------------------------------------------------

NEWS_ANALYST_AGENT = LlmAgent(
stage_tools.tool_stage_news
           |__ tools.get_fmp_news

# ---------------------------------------------------------
# AGENT 3: Insider Analyst
# ---------------------------------------------------------

INSIDER_ANALYST_AGENT = LlmAgent(
stage_tools.tool_stage_insiders,
          |__ tools.get_bearish_insider_sales,

#
# ---------------------------------------------------------
# AGENT 4: Quant Coordinator (Final Decision)
# ---------------------------------------------------------
QUANT_COORDINATOR_AGENT = 
    stage_tools.tool_read_full_dossier


==== Schemas ===
# schemas/dossier.py — or wherever you keep models

from typing import List, Optional
from pydantic import BaseModel, Field
from datetime import datetime


# ------------------------------
# 1. INPUT DATA MODELS (Keep existing ones)
# ------------------------------
# -----------------------------
# 1. MODELS FOR BQ LOSERS
# -----------------------------
class MarketLoser(BaseModel):
class BiggestLosersReport(BaseModel):



----- MODELS For NEWS

class NewsArticle(BaseModel):
    date: str = Field(description="Publication date")
    title: str = Field(description="Headline")
    content: str = Field(default="", description="Snippet or body")

class StockNewsReport(BaseModel):
    ticker: str
    articles: List[NewsArticle]
    error_message: Optional[str] = None

--- MODELS FOR INSIDER TRADES

class InsiderTrade(BaseModel):
class InsiderTradingReport(BaseModel):

# ------------------------------
# 2. QUANT SIGNAL MODEL (NEW)
# ------------------------------
class QuantitativeSignal(BaseModel):

# ------------------------------
# 3. AGENT DECISION MODEL
# ------------------------------
class QuantDecision(BaseModel):
# ------------------------------
# 4. UNIFIED PipelineDossier
# ------------------------------
class PipelineDossier(BaseModel):



