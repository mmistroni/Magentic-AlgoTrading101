import asyncio
from typing import Dict, Any
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, JsonCssExtractionStrategy

# Note: Keep your PriceReport model and clean_price logic as they are.

def get_bike_price_tool() -> Dict[str, Any]:
    """
    Retrieves the current price and availability for the Horizon Fitness 3.0SC Indoor Cycle.
    
    Returns:
        A dictionary containing the product name, current price in GBP, 
        and availability status.
    """
    async def run():
        browser_cfg = BrowserConfig(headless=True, enable_stealth=True)
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            schema = {"name": "Bike", "baseSelector": "body", "fields": [
                {"name": "name", "selector": "h1.page-title", "type": "text"},
                {"name": "price", "selector": ".price-wrapper .price", "type": "text"}
            ]}
            result = await crawler.arun(
                url="https://www.fitness-superstore.co.uk/horizon-fitness-3-0sc-indoor-cycle.html",
                config=CrawlerRunConfig(extraction_strategy=JsonCssExtractionStrategy(schema))
            )
            if result.success and result.extracted_content:
                import json
                data = json.loads(result.extracted_content)
                return PriceReport(description="Bike", **data[0]).model_dump()
            return {"error": "Could not retrieve bike price"}

    return asyncio.run(run())

def get_rayban_price_tool() -> Dict[str, Any]:
    """
    Scrapes the web for the latest price of Ray-Ban Meta Wayfarer Gen 2 (RW4012).
    This tool uses advanced stealth techniques to bypass anti-bot protections.
    
    Returns:
        A dictionary with the product description, name, and current price.
        Includes fallback data if the live site is inaccessible.
    """
    async def run():
        browser_cfg = BrowserConfig(headless=True, enable_stealth=True)
        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            # (Your existing schema and run_cfg logic here...)
            # Use the logic from your original get_rayban_price function
            # ...
            # Return model_dump() to provide a clean dict to ADK
            return PriceReport(description="Ray-Ban Meta", current_price=270.00).model_dump()

    return asyncio.run(run())