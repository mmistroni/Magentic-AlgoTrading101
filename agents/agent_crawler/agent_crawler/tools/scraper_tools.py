import asyncio
import json
import re
from typing import Optional, Union

from typing import Dict, Any, Union
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, JsonCssExtractionStrategy
from crawl4ai import (
    AsyncWebCrawler, 
    BrowserConfig, 
    CrawlerRunConfig, 
    CacheMode, 
    LLMConfig
)

from crawl4ai.extraction_strategy import (
    LLMExtractionStrategy, 
    JsonCssExtractionStrategy
)
from pydantic import BaseModel, Field, field_validator, ConfigDict

# --- 1. DATA MODEL ---
class PriceReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    description: str
    product_name: str = Field(default="Unknown Product", alias="name")
    current_price: Union[float, str] = Field(default=0.0, alias="price")
    availability: bool = Field(default=False)
    currency: str = "GBP"

    @field_validator('current_price', mode='before')
    @classmethod
    def clean_price(cls, v):
        if v == "NOT_FOUND" or v is None: return 0.0
        if isinstance(v, (int, float)): return float(v)
        # Handle string prices like "£270.00" or "from £270"
        nums = re.findall(r"\d+\.\d+|\d+", str(v))
        return float(nums[0]) if nums else 0.0

# --- 1. BIKE TOOL ---
async def get_bike_price_tool() -> Dict[str, Any]:
    """
    Retrieves the current price and availability for the Horizon Fitness 3.0SC Indoor Cycle.
    
    Returns:
        A dictionary containing description, current_price (GBP), and status.
    """
    browser_cfg = BrowserConfig(headless=True, enable_stealth=True)
    
    # We use 'async with' directly inside the tool
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        schema = {
            "name": "Bike", 
            "baseSelector": "body", 
            "fields": [
                {"name": "name", "selector": "h1.page-title", "type": "text"},
                {"name": "price", "selector": ".price-wrapper .price", "type": "text"}
            ]
        }
        
        result = await crawler.arun(
            url="https://www.fitness-superstore.co.uk/horizon-fitness-3-0sc-indoor-cycle.html",
            config=CrawlerRunConfig(extraction_strategy=JsonCssExtractionStrategy(schema))
        )
        
        if result.success and result.extracted_content:
            data = json.loads(result.extracted_content)
            # We assume your PriceReport model is imported
            return PriceReport(description="Bike", **data[0]).model_dump()
            
        return {"description": "Bike", "current_price": 0.0, "status": "Error: Scrape Failed"}

# --- 2. RAY-BAN TOOL ---
import json
from typing import Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy
from pydantic import BaseModel

# Assuming PriceReport is defined elsewhere in your project
class PriceReport(BaseModel):
    description: str
    product_name: str
    current_price: float

import json
import asyncio
from typing import Dict, Any, List
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import JsonCssExtractionStrategy

async def get_rayban_price_tool() -> Dict[str, Any]:
    """
    Scrapes Ray-Ban Meta Wayfarer Gen 2 from multiple sources (Argos, Currys, EE).
    Aggregates results to bypass retailer-specific bot blocks.
    """
    browser_cfg = BrowserConfig(headless=True, enable_stealth=True)
    
    # 1. Define the targets and their unique 2026 CSS selectors
    sources = [
        {
            "name": "Argos",
            "url": "https://www.argos.co.uk/product/7768895",
            "selector": "li[data-test='product-price-primary'] h2"
        },
        {
            "name": "Currys",
            "url": "https://www.currys.co.uk/products/ray-ban-meta-wayfarer-gen-2-glasses-matte-black-with-clear-to-grey-transitions-lenses-large-10291870.html",
            "selector": ".price-tag, [data-testid='price-value'], .product-price"
        },
        {
            "name": "EE Store",
            "url": "https://ee.co.uk/wearables/eyewear/brand:Ray-Ban%20Meta",
            "selector": ".price-big, .product-price, .ee-price"
        }
    ]

    async def fetch_source(crawler, source):
        schema = {
            "name": f"{source['name']} Scraper",
            "baseSelector": "body",
            "fields": [{"name": "price", "selector": source['selector'], "type": "text"}]
        }
        run_cfg = CrawlerRunConfig(
            extraction_strategy=JsonCssExtractionStrategy(schema),
            magic=True,
            cache_mode=CacheMode.BYPASS
        )
        try:
            result = await crawler.arun(url=source['url'], config=run_cfg)
            if result.success and result.extracted_content:
                data = json.loads(result.extracted_content)
                if data and data[0].get("price"):
                    price_str = data[0]["price"].replace("£", "").replace(",", "").strip()
                    return {"site": source['name'], "price": float(price_str)}
        except Exception:
            return None
        return None

    # 2. Run all scrapes in parallel using one browser session
    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        tasks = [fetch_source(crawler, s) for s in sources]
        completed_tasks = await asyncio.gather(*tasks)
        
        # Filter for successful results
        valid_hits = [r for r in completed_tasks if r and r['price'] > 0]

    # 3. Decision Logic
    if valid_hits:
        # Sort by lowest price if multiple sources work (Bonus technical signal!)
        best_deal = min(valid_hits, key=lambda x: x['price'])
        return PriceReport(
            description=f"Live Price from {best_deal['site']}",
            product_name="Ray-Ban Meta Wayfarer Gen 2",
            current_price=best_deal['price'],
            is_live=True
        ).model_dump()

    # 4. Final Fallback (If all 3 sites block the Cloud Run IP)
    return PriceReport(
        description="Ray-Ban Meta Wayfarer Gen 2 (Global Extraction Fallback)",
        product_name="Manual Check Required",
        current_price=299.0,
        is_live=False
    ).model_dump()