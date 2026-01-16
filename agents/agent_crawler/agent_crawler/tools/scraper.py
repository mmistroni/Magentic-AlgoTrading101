import asyncio
import json
import sys
from typing import Optional
from pydantic import BaseModel, Field, field_validator
from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from crawl4ai.extraction_strategy import LLMExtractionStrategy

# --- 1. THE DATA MODEL ---
class PriceReport(BaseModel):
    product_name: str = Field(description="The name of the fitness equipment")
    current_price: float = Field(description="The current sale price as a float")
    availability: bool = Field(description="True if the item is in stock")
    currency: str = "GBP"
    target_met: bool = False

    @field_validator('current_price', mode='before')
    @classmethod
    def clean_price(cls, v):
        # If the LLM returns a string like "£569.99", we clean it
        if isinstance(v, str):
            import re
            match = re.search(r"(\d+\.?\d*)", v.replace(',', ''))
            return float(match.group(1)) if match else 0.0
        return v

# --- 2. THE CRAWLER & AGENT LOGIC ---
async def get_price_json():
    # Browser config for Dev Containers / Cloud Run
    browser_cfg = BrowserConfig(
        headless=True,
        extra_args=["--no-sandbox", "--disable-dev-shm-usage", "--disable-gpu"]
    )

    # We use LLMExtractionStrategy to 'read' the page content
    # This avoids the CSS selector 'Field Required' errors
    extraction_strategy = LLMExtractionStrategy(
        provider="openai/gpt-4o", # You can use your preferred provider/model
        instruction="Extract the product name, the lowest 'Our Price', and if it is in stock.",
        schema_json=PriceReport.model_json_schema()
    )

    run_cfg = CrawlerRunConfig(
        extraction_strategy=extraction_strategy,
        cache_mode=CacheMode.BYPASS
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(
            url="https://www.fitness-superstore.co.uk/horizon-fitness-3-0sc-indoor-cycle.html",
            config=run_cfg
        )

        if result.success and result.extracted_content:
            # LLM extraction returns a list of results
            raw_data = json.loads(result.extracted_content)
            if raw_data:
                # We take the first result and validate with Pydantic
                report = PriceReport(**raw_data[0])
                
                # Business Logic for your March Budget
                if report.current_price < 500.0:
                    report.target_met = True
                
                return report.model_dump_json()
        
        return json.dumps({"error": "LLM failed to extract data", "success": False})

# --- 3. MAIN ---
if __name__ == "__main__":
    try:
        # Run the async scraper and print only the JSON result
        output = asyncio.run(get_price_json())
        print(output)
    except Exception as e:
        # Guarantee a JSON response even on crash
        print(json.dumps({"error": str(e), "success": False}))