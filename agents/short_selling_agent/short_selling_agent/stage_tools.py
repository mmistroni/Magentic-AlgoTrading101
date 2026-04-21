# agent_tools.py
from google.cloud import bigquery

# 1. Import your original tools
from short_selling_agent.tools import get_fmp_news, get_bearish_insider_sales
from short_selling_agent.schemas import MarketLoser

# 2. IMPORT THE SHARED STATE FROM FILE 1
from state import CURRENT_RUN_STATE 

from google.cloud import bigquery
from short_selling_agent.tools import get_fmp_news, get_bearish_insider_sales
from short_selling_agent.schemas import MarketLoser
from state import CURRENT_RUN_STATE 
import os
import logging
from google.cloud import bigquery
from short_selling_agent.schemas import Plus500UniverseReport



# --- AGENT 1'S ONLY TOOL ---
def tool_fetch_bq_candidates() -> str:
    """
    Fetches the market losers from BigQuery and saves them to the shared state.
    Returns a comma-separated list of the tickers found.
    """
    client = bigquery.Client(project='datascience-projects')
    query = "SELECT ticker, price, change_pct FROM `datascience-projects.finviz_blacklist.fmp_daily_losers` LIMIT 3"
    results = client.query(query).result()
    
    tickers = []
    for row in results:
        loser = MarketLoser(ticker=row.ticker, price=row.price, change_pct=row.change_pct)
        CURRENT_RUN_STATE.dossier.market_losers.append(loser)
        tickers.append(row.ticker)
        
    # We return the list of tickers so Agent 1 can pass them to Agent 2!
    return f"Tickers loaded: {', '.join(tickers)}"

# --- AGENT 2'S ONLY TOOL ---
def tool_stage_news(ticker: str) -> str:
    """
    Fetches the most recent news headlines for a specific stock ticker and saves it to the dossier.
    """
    news_report = get_fmp_news(ticker)
    CURRENT_RUN_STATE.dossier.news_reports.append(news_report)
    return f"Success: News for {ticker} saved to state."

# --- AGENT 3'S ONLY TOOL ---
def tool_stage_insiders(ticker: str) -> str:
    """
    Fetches Form 4 Insider Sales for a specific stock ticker and saves it to the dossier.
    """
    insider_report = get_bearish_insider_sales(ticker)
    CURRENT_RUN_STATE.dossier.insider_reports.append(insider_report)
    return f"Success: Insiders for {ticker} saved to state."

# --- AGENT 4'S ONLY TOOL ---
def tool_read_full_dossier() -> str:
    """
    Returns the complete JSON dataset of all staged Market Data, News, and Insider Sales.
    """
    return CURRENT_RUN_STATE.dossier.model_dump_json(indent=2)


def get_plus500_universe() -> Plus500UniverseReport:
    """
    Fetches the complete universe of tradable stocks from the Plus500 BigQuery table.
    
    Returns:
        Plus500UniverseReport: A Pydantic model containing a list of valid tickers.
    """
    logging.info("Fetching Plus500 tradable universe from BigQuery...")
    
    # You can hardcode this or use the env variable
    project_id = os.environ.get("GCP_PROJECT_ID", "datascience-projects")
    table_id = f"{project_id}.gcp_shareloader.plus500"
    
    try:
        client = bigquery.Client(project=project_id)
        
        # Querying the ticker/symbol column. 
        # (If your exact column name is 'symbol', change 'ticker' to 'symbol' below)
        query = f"""
            SELECT DISTINCT ticker 
            FROM `{table_id}`
            WHERE ticker IS NOT NULL
        """
        
        query_job = client.query(query)
        results = query_job.result()
        
        # Extract tickers into a clean list, converting to uppercase just in case
        valid_tickers = [row.ticker.strip().upper() for row in results if row.ticker]
        
        logging.info(f"Successfully loaded {len(valid_tickers)} tradable stocks from Plus500.")
        return Plus500UniverseReport(tickers=valid_tickers)

    except Exception as e:
        logging.error(f"Failed to fetch Plus500 universe: {str(e)}")
        return Plus500UniverseReport(tickers=[], error_message=str(e))