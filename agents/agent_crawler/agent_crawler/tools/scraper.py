import asyncio
import json
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# --- 1. THE FAIL-SAFE DATA MODEL ---
class PriceReport(BaseModel):
    # We add default values so "Field Required" errors are impossible
    product_name: str = "Horizon 3.0SC Studio Bike"
    current_price: float = 0.0 
    availability: bool = False
    currency: str = "GBP"
    target_met: bool = False

    @field_validator('current_price', mode='before')
    @classmethod
    def clean_price(cls, v):
        if not v: return 0.0
        if isinstance(v, str):
            match = re.search(r"(\d+\.?\d*)", v.replace(',', ''))
            return float(match.group(1)) if match else 0.0
        return v

    @field_validator('availability', mode='before')
    @classmethod
    def clean_availability(cls, v):
        if not v: return False
        return "in stock" in str(v).lower()

# --- 2. THE CSS SCRAPER (Zero Token Cost) ---
async def get_price_json():
    schema = {
        "name": "FSS_Price",
        "baseSelector": "body", # Broadest selector to find data anywhere
        "fields": [
            {"name": "product_name", "selector": "h1.page-title", "type": "text"},
            {"name": "current_price", "selector": ".price-wrapper .price, [data-price-amount]", "type": "text"},
            {"name": "availability", "selector": ".stock.available", "type": "text"}
        ]
    }

    browser_cfg = BrowserConfig(
        headless=True,
        extra_args=["--no-sandbox", "--disable-dev-shm-usage"]
    )

    # NO LLM STRATEGY HERE = NO RATE LIMITS
    run_cfg = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(schema),
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(
            url="https://www.fitness-superstore.co.uk/horizon-fitness-3-0sc-indoor-cycle.html",
            config=run_cfg
        )

        if result.success and result.extracted_content:
            raw_list = json.loads(result.extracted_content)
            if raw_list:
                # Use the fail-safe model to handle any empty data
                report = PriceReport(**raw_list[0])
                
                # Logic: Check price if we actually found one
                if 0 < report.current_price < 500.0:
                    report.target_met = True
                
                return report.model_dump_json()
        
        return json.dumps({"error": "CSS Extraction failed", "success": False})

if __name__ == "__main__":
    try:
        print(asyncio.run(get_price_json()))
    except Exception as e:
        print(json.dumps({"error": str(e), "success": False}))