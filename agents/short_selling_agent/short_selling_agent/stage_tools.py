# agent_tools.py
from google.cloud import bigquery

# 1. Import your original tools
from short_selling_agent.tools import get_fmp_news, get_bearish_insider_sales
from short_selling_agent.schemas import MarketLoser

# 2. IMPORT THE SHARED STATE FROM FILE 1
from state import CURRENT_RUN_STATE 

def tool_fetch_bq_candidates() -> str:
    """Fetches BigQuery candidates and saves them to the global state."""
    client = bigquery.Client(project='datascience-projects')
    query = "SELECT ticker, price, change_pct FROM `datascience-projects.finviz_blacklist.fmp_daily_losers` LIMIT 3"
    results = client.query(query).result()
    
    for row in results:
        loser = MarketLoser(ticker=row.ticker, price=row.price, change_pct=row.change_pct)
        # We are modifying the shared memory bank!
        CURRENT_RUN_STATE.dossier.market_losers.append(loser)
        
    return "SUCCESS: Loaded market losers into the Pipeline Dossier."

def tool_get_staged_tickers() -> str:
    """Tells the agent which tickers to analyze."""
    # We read from the shared memory bank!
    tickers = [loser.ticker for loser in CURRENT_RUN_STATE.dossier.market_losers]
    return f"TICKERS TO ANALYZE: {', '.join(tickers)}"

def tool_stage_news(ticker: str) -> str:
    """Fetches news and saves it to the global state."""
    # Call your original tool
    news_report = get_fmp_news(ticker) 
    # Modify the shared memory bank!
    CURRENT_RUN_STATE.dossier.news_reports.append(news_report)
    return f"SUCCESS: News for {ticker} appended to dossier."

def tool_stage_insiders(ticker: str) -> str:
    """Fetches insider sales and saves it to the global state."""
    insider_report = get_bearish_insider_sales(ticker)
    CURRENT_RUN_STATE.dossier.insider_reports.append(insider_report)
    return f"SUCCESS: Form 4 Insider data for {ticker} appended to dossier."

def tool_read_full_dossier() -> str:
    """Dumps the entire global state to a JSON string for the Quant to read."""
    # Read the final state and give it to the LLM!
    return CURRENT_RUN_STATE.dossier.model_dump_json(indent=2)