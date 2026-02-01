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
import re
from typing import Annotated
from pydantic import BaseModel, Field, BeforeValidator, AliasChoices

# 1. Define the cleaning function
def clean_currency(v: any) -> any:
    if isinstance(v, str):
        # Remove anything that isn't a digit, a dot, or a comma
        cleaned = re.sub(r'[^\d.]', '', v)
        return cleaned
    return v

# 2. Update your PriceReport model
class PriceReport(BaseModel):
    description: str
    
    # Keeps your alias fix from before
    product_name: str = Field(
        validation_alias=AliasChoices('product_name', 'name')
    )
    
    # This magic line cleans "£799.00" into "799.00" before validation
    current_price: Annotated[float, BeforeValidator(clean_currency)] = Field(
        validation_alias=AliasChoices('current_price', 'price')
    )


# --- 1. BIKE TOOL ---
import json
import re
from typing import Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, JsonCssExtractionStrategy

def clean_price_string(price_str: str) -> float:
    """Helper to turn '£799.00' or 'from £750' into 799.00"""
    if not price_str:
        return 0.0
    cleaned = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

import json
import re
import os
from typing import Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, JsonCssExtractionStrategy, CacheMode

def clean_price_string(price_str: str) -> float:
    if not price_str: return 0.0
    cleaned = re.sub(r'[^\d.]', '', price_str)
    try:
        return float(cleaned) if cleaned else 0.0
    except ValueError:
        return 0.0

async def get_bike_price_tool() -> Dict[str, Any]:
    browser_cfg = BrowserConfig(
        headless=True,
        enable_stealth=True,
        # Real-world User-Agent to bypass "All sources failed"
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36",
        extra_args=["--disable-dev-shm-usage", "--no-sandbox", "--disable-blink-features=AutomationControlled"]
    )

    sources = [
        {
            "name": "PriceSpy",
            "url": "https://pricespy.co.uk/search?search=Horizon%20Fitness%203.0SC",
            "selector": {
                "name": "ComparisonData",
                "baseSelector": "div[class*='ProductCard'], [data-testid='ProductCard']", # Fuzzy match classes
                "fields": [
                    {"name": "name", "selector": "h3", "type": "text"},
                    {"name": "price", "selector": "[data-testid='PriceLabel'], span[class*='Price']", "type": "text"}
                ]
            }
        },
        {
            "name": "Google Shopping",
            "url": "https://www.google.com/search?tbm=shop&q=Horizon+Fitness+3.0SC+Indoor+Cycle&gl=uk&hl=en",
            "selector": {
                "name": "ComparisonData",
                "baseSelector": ".sh-dgr__content",
                "fields": [
                    {"name": "name", "selector": "h3", "type": "text"},
                    {"name": "price", "selector": "span.a8S3wf, .r0C6Asf", "type": "text"}
                ]
            }
        }
    ]

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        for source in sources:
            print(f"--- Attempting {source['name']} ---")
            
            result = await crawler.arun(
                url=source["url"],
                config=CrawlerRunConfig(
                    extraction_strategy=JsonCssExtractionStrategy(source["selector"]),
                    wait_until="networkidle",
                    cache_mode=CacheMode.BYPASS,
                    # 'wait_for' accepts a CSS selector or a time in seconds (as a string)
                    wait_for="10", # Wait 5 seconds for JS to settle
                )
            )

            # 1. Try CSS Extraction first (Cheap/Fast)
            if result.success and result.extracted_content:
                data = json.loads(result.extracted_content)
                valid_items = [i for i in data if "horizon" in i.get("name", "").lower()]
                if valid_items:
                    item = valid_items[0]
                    return PriceReport(
                        description=f"Bike (Source: {source['name']})",
                        product_name=item.get("name"),
                        current_price=clean_price_string(item.get("price"))
                    ).model_dump()

            # 2. EMERGENCY FALLBACK: LLM Raw Text Extraction
            # If CSS failed, use the Markdown result.
            print(f"⚠️ {source['name']} CSS failed. Trying LLM extraction from Markdown...")
            if result.success and result.markdown:
                # We return the raw markdown to the Agent. 
                # Pydantic AI's Agent will then see this text and can extract the price itself.
                return {
                    "description": f"Raw Data from {source['name']}",
                    "raw_text": result.markdown[:2000], # Send a snippet to save tokens
                    "status": "CSS Failed - LLM Parsing Required"
                }

        return {"description": "Bike", "current_price": 0.0, "status": "Error: All sources and fallbacks failed"}



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
        '''
        tasks = [fetch_source(crawler, s) for s in sources]
        completed_tasks = await asyncio.gather(*tasks)
        '''
        results = []
        for source in sources:
            res = await fetch_source(crawler, source)
            if res: results.append(res)
                # Filter for successful results
        valid_hits = [r for r in results if r and r['price'] > 0]

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