import asyncio
import json
import re
from typing import Optional, Union

from google.cloud import storage

# --- 1. PERSISTENCE LOGIC (The "Memory" for Cloud Run) ---
def check_price_history(product_name: str, current_price: float):
    """Checks GCS to see if the price has dropped since last week."""
    bucket_name = os.getenv("GCS_BUCKET_NAME", "your-bucket-name")
    client = storage.Client()
    bucket = client.bucket(bucket_name)
    blob = bucket.blob("price_history.json")

    # Load history
    history = {}
    if blob.exists():
        history = json.loads(blob.download_as_text())

    # Compare
    prev_data = history.get(product_name, {})
    old_price = prev_data.get("price")
    
    trend = "First check"
    if old_price:
        if current_price < old_price:
            trend = f"🚨 PRICE DROP! (Down from £{old_price})"
        elif current_price > old_price:
            trend = f"Price increased (Was £{old_price})"
        else:
            trend = "Stable"

    # Save for next week
    history[product_name] = {"price": current_price}
    blob.upload_from_string(json.dumps(history))
    
    return trend