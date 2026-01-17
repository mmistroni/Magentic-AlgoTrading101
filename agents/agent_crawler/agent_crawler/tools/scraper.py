import asyncio
import json
import re
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

# --- 1. THE CORE DATA MODEL (Leveraged from yesterday) ---
class PriceReport(BaseModel):
    description: str  # To distinguish between Bike, Glasses, etc.
    product_name: str = "Unknown"
    current_price: float = 0.0 
    availability: bool = False
    currency: str = "GBP"

    @field_validator('current_price', mode='before')
    @classmethod
    def clean_price(cls, v):
        if not v: return 0.0
        if isinstance(v, str):
            match = re.search(r"(\d+\.?\d*)", v.replace(',', ''))
            return float(match.group(1)) if match else 0.0
        return v

# --- 2. SPECIALIZED TOOLS ---

async def get_bike_price() -> PriceReport:
    """Specialized tool for the Horizon 3.0SC Bike."""
    schema = {
        "name": "Bike_Scraper",
        "baseSelector": "body",
        "fields": [
            {"name": "product_name", "selector": "h1.page-title", "type": "text"},
            {"name": "current_price", "selector": ".price-wrapper .price", "type": "text"},
            {"name": "availability", "selector": ".stock.available", "type": "text"}
        ]
    }
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://www.fitness-superstore.co.uk/horizon-fitness-3-0sc-indoor-cycle.html",
            config=CrawlerRunConfig(extraction_strategy=JsonCssExtractionStrategy(schema))
        )
        data = json.loads(result.extracted_content)[0] if result.success else {}
        return PriceReport(description="Fitness Bike", **data)

async def get_rayban_price() -> PriceReport:
    """Specialized tool for Sunglass Hut Meta Wayfarers."""
    schema = {
        "name": "RayBan_Scraper",
        "baseSelector": "body",
        "fields": [
            {"name": "product_name", "selector": ".pdp-info__name", "type": "text"},
            {"name": "current_price", "selector": ".pdp-info__price", "type": "text"},
            {"name": "availability", "selector": ".pdp-buy-box__availability", "type": "text"}
        ]
    }
    
    async with AsyncWebCrawler() as crawler:
        result = await crawler.arun(
            url="https://www.sunglasshut.com/uk/ray-ban-meta/rw4012-8056262721421",
            config=CrawlerRunConfig(extraction_strategy=JsonCssExtractionStrategy(schema))
        )
        data = json.loads(result.extracted_content)[0] if result.success else {}
        return PriceReport(description="Smart Glasses", **data)

# --- 3. THE AGENT ORCHESTRATOR ---
async def main():
    # You can now call these individually without any "if-else" mess
    bike_info = await get_bike_price()
    glasses_info = await get_rayban_price()

    print(f"--- Results ---")
    print(f"{bike_info.description}: {bike_info.current_price}")
    print(f"{glasses_info.description}: {glasses_info.current_price}")

if __name__ == "__main__":
    asyncio.run(main())