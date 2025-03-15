from openbb import obb
from langchain.tools import Tool
import reticker

def get_ticker_from_query(query):
    extractor = reticker.TickerExtractor(deduplicate=True)
    tickers = extractor.extract(query)
    if len(tickers) > 1:
        return ','.join(tickers)
    return tickers[0] 


def get_stock_price(query: str) -> str:
    """Get the current stock price for a given ticker."""
    try:
        ticker = get_ticker_from_query(query)
        data = obb.equity.price.quote(symbol=ticker).to_df().to_dict('records')[0]
        return f"The current price of {ticker} is ${data['close']:.2f}"
    except Exception as e:
        return f"Error fetching stock price for {ticker}: {str(e)}"

def get_company_overview(query: str) -> str:
    """Get an overview of a company for a given ticker."""
    try:
        ticker = get_ticker_from_query(query)
        data = obb.equity.profile(symbol=ticker)
        return f"Latest Overview for {ticker} are that i don thave anything "
    except Exception as e:
        return f"Error fetching company overview for {ticker}: {str(e)}"

def get_latest_news_for_company(query : str) -> str:
    """ Get latest news for a company """
    try:
        ticker = get_ticker_from_query(query)
        return f"I dont have any news for now"
    except Exception as e:
        return f"Error fetching stock price for {ticker}: {str(e)}"




# Create LangChain tools
obb_tools = [
    Tool(
        name="StockPrice",
        func=get_stock_price,
        description="Useful for getting the current stock price of a company. Input should be a stock ticker symbol."
    ),
    Tool(
        name="CompanyOverview",
        func=get_company_overview,
        description="Useful for getting an overview of a company. Input should be a stock ticker symbol."
    ),
    Tool(
        name="CompanyNews",
        func=get_latest_news_for_company,
        description="Useful for getting latest news for a company. Input should be a stock ticker symbol."
    )

]