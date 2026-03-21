import json
import requests
from .finviz_tools import get_short_sell_filter
import os


# --- STEP 1: FINVIZ SCRAPER ---
def get_finviz_targets():
    print("Step 1: Scraping Finviz...")
    # The 'Strict' Short Filter: Small Cap+, High Debt, Negative Growth, Inst Trap, Breakdown
    
    finviz_screens = get_finviz_targets()
    
    tickers = []
    try:
        for data in finviz_screens:
            if 'ticker' in data:
                tickers.append(data['ticker'].strip())
        return tickers
    except Exception as e:
        print(f"Error scraping Finviz: {e}")
        return []

# --- STEP 2: FMP NEWS FETCH ---
def get_fmp_news(ticker):
    print(f"Step 2: Fetching news for {ticker}...")
    url = f"https://financialmodelingprep.com/api/v3/stock-news?tickers={ticker}&limit=10&apikey={os.environ['FMP_API_KEY']}"
    try:
        data = requests.get(url).json()
        if not data: return None
        
        # Format for LLM
        news_text = ""
        for item in data:
            news_text += f"- {item['publishedDate']}: {item['title']}\n"
        return news_text
    except Exception as e:
        print(f"Error FMP: {e}")
        return None

# --- STEP 3: LLM AGENT ANALYSIS ---
def analyze_with_agent(ticker, news_text):
    print(f"Step 3: Agent analyzing {ticker}...")
    
    prompt = f"""
    You are a Hedge Fund Short-Seller. Analyze this news for {ticker}.
    The stock is technically broken (High Debt, Downtrend).
    
    Look for specific negative catalysts:
    - Dilution / Offerings
    - Lawsuits / SEC Investigations
    - Earnings Miss / Guidance Cuts
    - CFO/CEO Resignation
    
    NEWS DATA:
    {news_text}
    
    OUTPUT JSON ONLY:
    {{
        "ticker": "{ticker}",
        "short_score": (0-10, where 10 is immediate short),
        "catalyst": "String description",
        "action": "SHORT" or "WAIT"
    }}
    """
    
    try:
        #response = model.generate_content(prompt)
        # Clean response to ensure valid JSON
        #clean_json = response.text.replace("```json", "").replace("```", "").strip()
        #return json.loads(clean_json)
        return None
    except Exception as e:
        print(f"Agent Error: {e}")
        return None

# --- MAIN EXECUTION ---
def main():
    # 1. Get List
    candidates = get_finviz_targets()
    
    final_report = []
    
    # 2. Loop & Analyze
    for ticker in candidates:
        news = get_fmp_news(ticker)
        if news:
            analysis = analyze_with_agent(ticker, news)
            if analysis and analysis.get('short_score', 0) >= 7:
                final_report.append(analysis)
                print(f"*** HIT: {ticker} Score: {analysis['short_score']} ***")
        else:
            print(f"No news for {ticker}, skipping Agent.")
        import time
        time.sleep(1) # Be nice to APIs
        
    # 3. Output Results (Log to Cloud Logging / Save to DB)
    print("\n--- FINAL SHORT REPORT ---")
    print(json.dumps(final_report, indent=2))
