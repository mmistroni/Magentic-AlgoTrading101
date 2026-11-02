import logging
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)

def get_institutional_holders_percentage_yahoo(ticker: str) -> float:
    """
    Scrapes Yahoo Finance to retrieve the institutional ownership percentage 
    for a given ticker symbol. Returns a float (e.g. 0.85 for 85%), or 
    a safe default (0.55555) if scraping fails.
    """
    try:
        link = f'https://finance.yahoo.com/quote/{ticker}/holders'
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
        r = requests.get(link, headers=headers, timeout=5)
        if r.status_code != 200:
            return 0.55555
            
        bs = BeautifulSoup(r.content, 'html.parser')
        spans = bs.find_all('span')

        matching_spans = [s for s in spans if 'of Shares Held by Institutions' in (s.text or '')]
        if not matching_spans:
            return 0.55555
            
        row = matching_spans[0].parent.parent
        pcnt_text = row.find_all('td')[0].text.strip()
        
        # Strip trailing '%' and convert to decimal float
        return float(pcnt_text.replace('%', '')) / 100.0
    except Exception as e:
        logger.debug(f"Could not fetch Yahoo institutional holders for {ticker}: {e}")
        return 0.55555  # Safe default fallback