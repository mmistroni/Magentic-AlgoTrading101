import asyncio
import json
import re
from typing import Optional, Union
import os
import json
from google.cloud import storage, bigquery
from google.adk.tools import FunctionTool


from google.cloud import storage

# --- 1. PERSISTENCE LOGIC (The "Memory" for Cloud Run) ---
import os
import json
from google.cloud import storage

def check_price_history(product_name: str, current_price: float) -> dict:
    """
    Compares the current product price against historical data stored in GCS.
    
    This tool retrieves the last recorded price for a specific product from a 
    persistent JSON file in Google Cloud Storage. It calculates the price trend 
    (drop, increase, or stable) and updates the history with the new price for 
    future weekly tracking.
    
    Args:
        product_name (str): The exact name or model of the product to track.
        current_price (float): The latest found price to compare and persist.
        
    Returns:
        dict: A summary of the price analysis containing:
            - trend (str): A human-readable description of the price change.
            - previous_price (float or None): The last price found, if any.
            - status (str): 'success' if history was updated, 'error' otherwise.
    """
    bucket_name = os.getenv("GCS_BUCKET_NAME", "mm_dataflow_bucket")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob("price_history.json")

    # Load history
    history = {}
    try:
        if blob.exists():
            history = json.loads(blob.download_as_text())
    except Exception as e:
        return {"trend": "Error loading history", "status": f"error: {str(e)}"}

    # Compare
    prev_data = history.get(product_name, {})
    old_price = prev_data.get("price")
    
    trend_msg = "First check - New item added to tracking."
    if old_price is not None:
        if current_price < old_price:
            trend_msg = f"🚨 PRICE DROP! (Previously £{old_price})"
        elif current_price > old_price:
            trend_msg = f"Price increased (Previously £{old_price})"
        else:
            trend_msg = "Price is stable since last week."

    # Save for next week
    history[product_name] = {"price": current_price}
    blob.upload_from_string(json.dumps(history))
    
    return {
        "trend": trend_msg,
        "previous_price": old_price,
        "status": "success"
    }

async def track_and_log_price(product_name: str, current_price: float, retailer: str) -> dict:
    """
    Performs a weekly price comparison and persists the data to BigQuery and GCS.
    
    This tool is a critical second step in the price discovery workflow. It retrieves 
    historical price data from Google Cloud Storage to determine if the price has 
    dropped or increased since the last run. It then logs the final verified 
    discovery—including the current price, previous price, and retailer—into 
    a permanent BigQuery table for long-term tracking.
    
    Args:
        product_name (str): The specific name or model of the product being tracked.
        current_price (float): The market low price found during the search phase.
        retailer (str): The name of the retailer offering the current_price.
        
    Returns:
        dict: A summary of the tracking operation containing:
            - trend (str): Description of the price movement (DROPPED, INCREASED, Stable).
            - difference (float): The numerical change in price from last week.
            - last_week (float or None): The price recorded in the previous session.
    """    
    # --- Part A: GCS History Check (Weekly Comparison) ---
    bucket_name = os.getenv("GCS_BUCKET_NAME", "mm_dataflow_bucket")
    storage_client = storage.Client()
    blob = storage_client.bucket(bucket_name).blob("weekly_history.json")
    
    history = json.loads(blob.download_as_text()) if blob.exists() else {}
    last_week = history.get(product_name, {})
    prev_price = last_week.get("price")
    
    # Calculate Trend
    diff = current_price - prev_price if prev_price else 0
    trend = "Stable"
    if prev_price:
        if current_price < prev_price: trend = "DROPPED"
        elif current_price > prev_price: trend = "INCREASED"

    # --- Part B: BigQuery Logging (Permanent Record) ---
    bq_client = bigquery.Client()
    table_id = os.getenv("BQ_TABLE_ID", "datascience-projects.gcp_shareloader.price_history")
    
    row = [{
        "product_name": product_name,
        "current_price": current_price,
        "previous_price": prev_price,
        "price_diff": diff,
        "trend_status": trend,
        "retailer": retailer
    }]
    
    bq_client.insert_rows_json(table_id, row)

    # --- Part C: Update JSON for next week ---
    history[product_name] = {"price": current_price}
    blob.upload_from_string(json.dumps(history))

    return {"trend": trend, "difference": diff, "last_week": prev_price}