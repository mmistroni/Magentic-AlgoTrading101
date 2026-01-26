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

async def get_rayban_price_tool() -> Dict[str, Any]:
    """
    Scrapes the price of Ray-Ban Meta Wayfarer Gen 2 from Argos.
    Includes robust selectors and fallback data for the Feature Agent.
    """
    browser_cfg = BrowserConfig(
        headless=True,
        enable_stealth=True,
    )

    # Specific URL for the Matte Black Wayfarer Gen 2 to ensure accuracy
    url = "https://www.argos.co.uk/product/7768895"

    # Argos 2026 uses specific data-test attributes for their price and titles
    schema = {
        "name": "Argos Price Scraper",
        "baseSelector": "main",
        "fields": [
            {
                "name": "product_name", 
                "selector": "span[data-test='product-title']", 
                "type": "text"
            },
            {
                "name": "price_text", 
                "selector": "li[data-test='product-price-primary'] h2", 
                "type": "text"
            }
        ]
    }

    run_cfg = CrawlerRunConfig(
        extraction_strategy=JsonCssExtractionStrategy(schema),
        magic=True,
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)

        # 1. Handle Failed Connection/Scrape
        if not result.success:
            print(f"DEBUG: Argos Scrape failed. Status: {result.status_code}")
            return PriceReport(
                description="Ray-Ban Meta Wayfarer Gen 2 (Error Fallback)", 
                product_name="Site Unavailable", 
                current_price=299.00  # Conservative fallback
            ).model_dump()

        # 2. Process Extracted Content
        if result.extracted_content:
            raw_data = json.loads(result.extracted_content)
            if raw_data and len(raw_data) > 0:
                item = raw_data[0]
                # Clean the price string (e.g., "£299.00" -> 299.0)
                price_str = item.get("price_text", "0").replace("£", "").replace(",", "")
                try:
                    price_val = float(price_str)
                except ValueError:
                    price_val = 0.0

                return PriceReport(
                    description="Live Price from Argos",
                    product_name=item.get("product_name", "Ray-Ban Meta Wayfarer Gen 2"),
                    current_price=price_val
                ).model_dump()

        # 3. Fallback for successful crawl but failed extraction
        return PriceReport(
            description="Ray-Ban Meta Wayfarer Gen 2 (Extraction Fallback)", 
            product_name="Manual Check Required", 
            current_price=299.00
        ).model_dump()
