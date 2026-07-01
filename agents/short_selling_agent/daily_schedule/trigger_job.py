import os
import sys
import json
import logging
from google.cloud import bigquery
from google.api_core.exceptions import GoogleAPIError

# Initialize logging context
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("quant_pipeline_job")

def check_plus500_availability(ticker_decisions: list) -> list:
    """
    Queries BigQuery to cross-reference proposed short assets against availability lists.
    Safely catches database infrastructure errors to prevent pipeline job crashes.
    """
    if not ticker_decisions:
        logger.info("No short candidates recommended by the agent. Skipping database lookup.")
        return []

    # Extract clean tickers to cross-reference
    tickers_to_check = [item["ticker"] for item in ticker_decisions if "ticker" in item]
    
    # Pre-configure your fallback empty result container
    available_tickers = []
    
    try:
        logger.info(f"Connecting to BigQuery to validate eligibility for: {tickers_to_check}")
        client = bigquery.Client()
        
        # Simple cross-reference query matching your availability catalog
        query = """
            SELECT ticker 
            FROM `your_project.your_dataset.plus500_shortable_instruments`
            WHERE ticker IN UNNEST(@tickers) AND is_available = TRUE
        """
        job_config = bigquery.QueryJobConfig(
            query_parameters=[
                bigquery.ArrayQueryParameter("tickers", "STRING", tickers_to_check)
            ]
        )
        
        query_job = client.query(query, job_config=job_config)
        results = query_job.result(timeout=30.0) # Explicit timeout threshold
        
        available_tickers = [row.ticker for row in results]
        logger.info(f"BigQuery validation successful. Match count: {len(available_tickers)}")

    except GoogleAPIError as gcp_err:
        # Catch any structural Google Cloud/BigQuery network or query exceptions safely
        logger.error(f"⚠️ BigQuery API Error encountered: {gcp_err}. Proceeding with an empty matching set.")
        # Fall back gracefully instead of raising an error
        available_tickers = []
        
    except Exception as ex:
        # General catch-all fallback loop for unexpected runtime execution blocks
        logger.error(f"⚠️ Unexpected infrastructure error inside validation step: {ex}.")
        available_tickers = []

    # Map validation results back over the agent's payload arrays
    filtered_decisions = [
        decision for decision in ticker_decisions 
        if decision.get("ticker") in available_tickers
    ]
    
    return filtered_decisions

def run_pipeline_orchestration(target_date: str):
    """Primary Cloud Run entry point runner."""
    logger.info(f"Starting short-selling analysis routine for: {target_date}")
    
    # --- 1. Simulate pulling the payload from your multi-agent workflow ---
    # (Imagine this came straight back from your newly updated Quant Coordinator)
    simulated_agent_raw_text = """
    {
      "final_decisions": [
        {"ticker": "SDOT", "conviction_score": 0.85, "action": "SHORT", "reasoning": "Severe structural catalyst drop."}
      ]
    }
    """
    
    try:
        agent_payload = json.loads(simulated_agent_raw_text.strip())
        proposed_shorts = agent_payload.get("final_decisions", [])
    except json.JSONDecodeError:
        logger.error("Failed to parse agent response string. Terminating execution.")
        sys.exit(1)

    # --- 2. Pass recommended items to our safe database validator ---
    final_executable_trades = check_plus500_availability(proposed_shorts)
    
    # --- 3. Clean Final Execution Logging Output ---
    if not final_executable_trades:
        logger.warning("🏁 Pipeline finished successfully: Zero assets passed validation filters today.")
        print(json.dumps({"status": "No candidates for shorting found", "final_decisions": []}))
    else:
        logger.info(f"🎯 Pipeline finished successfully. Executing {len(final_executable_trades)} target short entries.")
        print(json.dumps({"status": "SUCCESS", "final_decisions": final_executable_trades}, indent=2))

if __name__ == "__main__":
    run_pipeline_orchestration("2026-07-01")