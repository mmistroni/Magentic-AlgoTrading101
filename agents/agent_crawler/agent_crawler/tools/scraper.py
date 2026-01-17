import asyncio
import os
import json
import re
from typing import Optional, Union

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

# --- 1. THE REPAIRED DATA MODEL ---
class PriceReport(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    description: str
    product_name: str = Field(default="Unknown Product", alias="name")
    # We change price to Union to stop the crash if Gemini returns a string
    current_price: Union[float, str] = Field(default=0.0, alias="price")
    availability: bool = Field(default=False)
    currency: str = "GBP"

    @field_validator('current_price', mode='before')
    @classmethod
    def clean_price(cls, v):
        if v == "NOT_FOUND" or v is None: return 0.0
        if isinstance(v, (int, float)): return float(v)
        # Extract number from string like "£349.00"
        nums = re.findall(r"\d+\.\d+|\d+", str(v))
        return float(nums[0]) if nums else 0.0

# --- 2. THE TOOLS ---

async def get_bike_price(crawler: AsyncWebCrawler) -> PriceReport:
    # (Keeping this the same as it works!)
    schema = {"name": "Bike", "baseSelector": "body", "fields": [
        {"name": "name", "selector": "h1.page-title", "type": "text"},
        {"name": "price", "selector": ".price-wrapper .price", "type": "text"}
    ]}
    result = await crawler.arun(
        url="https://www.fitness-superstore.co.uk/horizon-fitness-3-0sc-indoor-cycle.html",
        config=CrawlerRunConfig(extraction_strategy=JsonCssExtractionStrategy(schema))
    )
    if result.success and result.extracted_content:
        return PriceReport(description="Bike", **json.loads(result.extracted_content)[0])
    return PriceReport(description="Bike", name="Error", price=0.0)

async def get_rayban_price(crawler: AsyncWebCrawler) -> PriceReport:
    """Enhanced tool with JS-Wait for Sunglass Hut."""
    llm_strategy = LLMExtractionStrategy(
        llm_config=LLMConfig(provider="gemini/gemini-1.5-flash", api_token=os.getenv("GEMINI_API_KEY")),
        schema=PriceReport.model_json_schema(),
        instruction="Extract the product name and current price. If you see 'Pardon our interruption', the site is blocked."
    )

    run_cfg = CrawlerRunConfig(
        extraction_strategy=llm_strategy,
        magic=True,
        cache_mode=CacheMode.BYPASS,
        # NEW: Specifically wait for the price currency symbol to appear in the HTML
        wait_for="js:document.body.innerText.includes('£')",
        page_timeout=60000,
        delay_before_return_html=5.0
    )

    result = await crawler.arun(
        url="https://www.sunglasshut.com/uk/ray-ban-meta/rw4012-8056262721421",
        config=run_cfg
    )

    if result.success and result.extracted_content:
        try:
            data = json.loads(result.extracted_content)
            item = data[0] if isinstance(data, list) else data
            return PriceReport(description="Ray-Ban Meta", **item)
        except Exception:
            pass
    
    return PriceReport(description="Ray-Ban Meta", name="SITE_TIMEOUT_OR_BLOCKED", price=0.0)

# --- 3. MAIN ---
async def main():
    browser_cfg = BrowserConfig(
        headless=True, 
        enable_stealth=True, 
        browser_type="chromium",
        # Use a high-quality User Agent
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        print("🚀 Running Parallel Scrape...")
        results = await asyncio.gather(get_bike_price(crawler), get_rayban_price(crawler))
        
        for r in results:
            print(f"---\nItem: {r.description}\nPrice: £{r.current_price}\nName: {r.product_name}")

if __name__ == "__main__":
    asyncio.run(main())