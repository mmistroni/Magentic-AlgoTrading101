# Assuming get_short_squeeze_filter is imported from your finviz_tools
from .finviz_tools import get_short_squeeze_filter 
from .schemas import BiggestLosersReport, InsiderTrade, BlacklistReport, MarketLoser, \
    StockNewsReport, InsiderTradingReport, NewsArticle

import logging
import requests
import os
from datetime import datetime, timedelta


def get_blacklist_targets() -> BlacklistReport:
    """
    Fetches a list of highly shorted, low-float stocks that pose a massive "short squeeze" risk.
    AGENT INSTRUCTIONS: Use this to get the 'Danger List'. Do not short these stocks.
    """
    logging.info("Step 1: Scraping Finviz for Squeeze Blacklist...")
    try:
        finviz_screens = get_short_squeeze_filter()
        tickers = [data['ticker'].strip() for data in finviz_screens if 'ticker' in data]
        logging.info(f'Fetched {len(tickers)} from blacklist')
        return BlacklistReport(tickers=tickers)
    except Exception as e:
        logging.error(f"Error scraping Finviz Blacklist: {e}")
        raise e


def get_fmp_bigger_losers() -> BiggestLosersReport:
    """
    Fetches the list of the biggest losing stocks in the market today.
    AGENT INSTRUCTIONS: Call this to find initial candidates that are gapping down.
    """
    fmp_url = f"https://financialmodelingprep.com/stable/biggest-losers?apikey={os.environ['FMP_API_KEY']}"
    try:
        data = requests.get(fmp_url).json()
        losers = []
        for item in data:
            losers.append(MarketLoser(
                ticker=item.get('symbol', ''),
                price=float(item.get('price', 0.0)),
                change_pct=float(item.get('changesPercentage', 0.0))
            ))
        return BiggestLosersReport(losers=losers)
    except Exception as e:
        logging.error(f"Failed to retrieve biggest losers: {str(e)}")
        return BiggestLosersReport(losers=[], error_message=str(e))


def get_fmp_news(ticker: str) -> StockNewsReport:
    """
    Fetches the most recent news headlines for a specific stock ticker.
    AGENT INSTRUCTIONS: Use this to determine if a price drop is caused by permanent damage.
    """
    logging.info(f"Fetching news for {ticker}...")
    api_key = os.environ.get('FMP_API_KEY')
    url = f"https://financialmodelingprep.com/api/v3/stock-news?tickers={ticker}&limit=10&apikey={api_key}"
    
    try:
        data = requests.get(url).json()
        if not data:
            return StockNewsReport(ticker=ticker, articles=[], error_message="No news found.")
            
        articles = [
            NewsArticle(date=item.get('publishedDate', ''), title=item.get('title', '')) 
            for item in data
        ]
        return StockNewsReport(ticker=ticker, articles=articles)
    except Exception as e:
        logging.error(f"Error FMP News API: {e}")
        return StockNewsReport(ticker=ticker, articles=[], error_message=str(e))


def get_bearish_insider_sales(ticker: str, days_back: int = 180, min_value: int = 250000) -> InsiderTradingReport:
    """
    Fetches SEC Form 4 insider trading data to detect C-Suite stock dumping.
    AGENT INSTRUCTIONS: Use this to verify management conviction. High dumping = high bearish score.
    """
    logging.info(f"Checking Form 4 Insider Sales for {ticker}...")
    api_key = os.environ.get('FMP_API_KEY')
    url = f"https://financialmodelingprep.com/api/v4/insider-trading?symbol={ticker}&page=0&apikey={api_key}"
    
    try:
        data = requests.get(url).json()
        if not data or not isinstance(data, list):
            return InsiderTradingReport(ticker=ticker, total_dollars_dumped=0.0, significant_sales=[], error_message="No insider activity found.")

        cutoff_date = datetime.now() - timedelta(days=days_back)
        significant_sales = []
        total_dollars_dumped = 0.0
        target_roles = ['CEO', 'CHIEF EXECUTIVE', 'CFO', 'CHIEF FINANCIAL', 'COO', 'PRESIDENT', 'DIRECTOR']

        for trade in data:
            tx_date_str = trade.get('transactionDate')
            if not tx_date_str or trade.get('transactionType') != 'S-Sale':
                continue
                
            tx_date = datetime.strptime(tx_date_str[:10], '%Y-%m-%d')
            if tx_date < cutoff_date:
                continue 

            shares = trade.get('securitiesTransacted', 0)
            price = trade.get('price', 0)
            if not shares or not price:
                continue
                
            dollar_value = float(shares) * float(price)
            if dollar_value < min_value:
                continue

            title = str(trade.get('typeOfOwner', '')).upper()
            if any(role in title for role in target_roles):
                total_dollars_dumped += dollar_value
                significant_sales.append(InsiderTrade(
                    date=tx_date_str[:10],
                    name=trade.get('reportingName', 'Unknown'),
                    title=title,
                    value_sold=dollar_value
                ))

        return InsiderTradingReport(
            ticker=ticker,
            total_dollars_dumped=round(total_dollars_dumped, 2),
            significant_sales=significant_sales
        )
    except Exception as e:
        logging.error(f"Error processing Form 4 data: {str(e)}")
        return InsiderTradingReport(ticker=ticker, total_dollars_dumped=0.0, significant_sales=[], error_message=str(e))

import requests
import logging

def get_squeeze_metrics(ticker: str):
    """Fetches Float and Short Interest from FMP for historical tracking."""
    short_pct = 0.0
    free_float = 999999999.0
    
    try:
        api_key = os.environ['FMP_API_KEY']
        # 1. Get Short Interest
        short_url = f"https://financialmodelingprep.com/api/v4/stock-short-interest?symbol={ticker}&apikey={api_key}"
        short_data = requests.get(short_url).json()
        if short_data and isinstance(short_data, list):
            short_pct = float(short_data[0].get('shortPercentOfFloat', 0))
            
        # 2. Get Float
        float_url = f"https://financialmodelingprep.com/api/v4/shares_float?symbol={ticker}&apikey={api_key}"
        float_data = requests.get(float_url).json()
        if float_data and isinstance(float_data, list):
            free_float = float(float_data[0].get('freeFloat', 999999999))
            
    except Exception as e:
        logging.warning(f"Failed to fetch squeeze metrics for {ticker}: {e}")
        
    return short_pct, free_float
