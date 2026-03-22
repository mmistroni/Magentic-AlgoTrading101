import os
import json
import logging
import requests
from datetime import datetime, timedelta
from .finviz_tools import get_short_squeeze_filter 

# Configure logging
logging.basicConfig(level=logging.INFO)


def get_blacklist_targets() -> list:
    """
    Fetches a list of highly shorted, low-float stocks that pose a massive "short squeeze" risk.
    
    AGENT INSTRUCTIONS:
    Call this tool to get the "Danger List." If you are evaluating a stock for a short-sell 
    position and its ticker appears in this list, you MUST reject the short trade immediately. 
    These stocks are ticking time bombs that could explode upward.
    
    Returns:
        list: A list of string ticker symbols (e.g., ['GME', 'AMC', 'CVNA']) that must NOT be shorted.
    """
    print("Step 1: Scraping Finviz for Squeeze Blacklist...")
    finviz_screens = get_short_squeeze_filter()
    
    tickers = []
    try:
        for data in finviz_screens:
            if 'ticker' in data:
                tickers.append(data['ticker'].strip())
        return tickers
    except Exception as e:
        print(f"Error scraping Finviz Blacklist: {e}")
        return []


def get_fmp_bigger_losers(fmp_api_key: str) -> list:
    """
    Fetches the list of the biggest losing stocks in the market today using the Financial Modeling Prep (FMP) API.
    
    AGENT INSTRUCTIONS:
    Call this tool at the beginning of your workflow to find initial candidates for short selling. 
    These are stocks that have gapped down significantly or are experiencing extreme negative momentum today.
    
    Args:
        fmp_api_key (str): The API key for Financial Modeling Prep.
        
    Returns:
        list: A list of dictionaries containing ticker data, price changes, and metrics for the biggest market losers.
    """
    fmp_url = f'https://financialmodelingprep.com/stable/biggest-losers?apikey={fmp_api_key}'

    try:
        data = requests.get(fmp_url).json()
        return data
    except Exception as e:
        logging.error(f'Failed to retrieve biggest losers: {str(e)}')
        return []


def get_fmp_news(ticker: str) -> str:
    """
    Fetches the most recent news headlines (last 10 articles) for a specific stock ticker.
    
    AGENT INSTRUCTIONS:
    Call this tool to find the fundamental catalyst behind a stock's price drop. 
    Read the returned headlines to determine if the drop is caused by permanent damage 
    (e.g., "Guidance Cut", "Dilution", "Lawsuit", "CFO Resigns") or temporary noise.
    
    Args:
        ticker (str): The stock ticker symbol to query (e.g., "AAPL", "KSS").
        
    Returns:
        str: A formatted string containing the publication dates and headlines of recent news. 
             Returns None if no news is found.
    """
    print(f"Step 2: Fetching news for {ticker}...")
    # Grabs API key from environment to prevent passing it around unnecessarily
    api_key = os.environ.get('FMP_API_KEY') 
    url = f"https://financialmodelingprep.com/api/v3/stock-news?tickers={ticker}&limit=10&apikey={api_key}"
    
    try:
        data = requests.get(url).json()
        if not data: 
            return None
        
        news_text = "RECENT HEADLINES:\n"
        for item in data:
            news_text += f"- {item['publishedDate']}: {item['title']}\n"
        return news_text
    except Exception as e:
        print(f"Error FMP News API: {e}")
        return None


def get_bearish_insider_sales(ticker: str, days_back: int = 180, min_value: int = 250000) -> str:
    """
    Fetches SEC Form 4 insider trading data to detect if C-Suite executives have been dumping massive amounts of stock.
    
    AGENT INSTRUCTIONS:
    Call this tool to verify management conviction. If executives (CEO, CFO, Directors) 
    have sold massive amounts of stock in the months leading up to a price drop, it is a 
    high-conviction bearish signal (they knew bad news was coming). 
    
    Args:
        ticker (str): The stock ticker symbol to query.
        days_back (int, optional): How many days back to look for insider selling. Defaults to 180.
        min_value (int, optional): The minimum dollar amount of the sale to be considered significant. Defaults to 250,000.
        
    Returns:
        str: A formatted string aggregating the total dollar amount dumped by top executives, 
             including specific transaction dates and titles.
    """
    print(f"Checking Form 4 Insider Sales for {ticker} (Last {days_back} days)...")
    
    api_key = os.environ.get('FMP_API_KEY')
    url = f"https://financialmodelingprep.com/api/v4/insider-trading?symbol={ticker}&page=0&apikey={api_key}"
    
    try:
        response = requests.get(url)
        data = response.json()
        
        if not data or not isinstance(data, list):
            return "No recent insider activity found."

        cutoff_date = datetime.now() - timedelta(days=days_back)
        
        significant_sales = []
        total_dollars_dumped = 0.0

        for trade in data:
            tx_date_str = trade.get('transactionDate')
            if not tx_date_str:
                continue
                
            tx_date = datetime.strptime(tx_date_str[:10], '%Y-%m-%d')
            if tx_date < cutoff_date:
                continue 

            if trade.get('transactionType') != 'S-Sale':
                continue

            shares_sold = trade.get('securitiesTransacted', 0)
            price = trade.get('price', 0)
            
            if not shares_sold or not price:
                continue
                
            dollar_value = float(shares_sold) * float(price)

            if dollar_value < min_value:
                continue

            title = str(trade.get('typeOfOwner', '')).upper()
            target_roles = ['CEO', 'CHIEF EXECUTIVE', 'CFO', 'CHIEF FINANCIAL', 'COO', 'PRESIDENT', 'DIRECTOR']
            is_top_brass = any(role in title for role in target_roles)
            
            if is_top_brass:
                total_dollars_dumped += dollar_value
                name = trade.get('reportingName', 'Unknown')
                
                sale_record = (
                    f"- {tx_date_str[:10]}: {name} ({title}) "
                    f"SOLD ${dollar_value:,.0f} (Shares: {float(shares_sold):,.0f} at ${float(price):.2f})"
                )
                significant_sales.append(sale_record)

        if not significant_sales:
            return f"No significant C-Suite selling (>${min_value:,}) detected in the last {days_back} days."
            
        output = f"MASSIVE INSIDER SELLING DETECTED: Total of ${total_dollars_dumped:,.0f} dumped by executives in the last {days_back} days.\n"
        output += "\n".join(significant_sales)
        
        return output

    except Exception as e:
        return f"Error processing Form 4 data: {str(e)}"