from openbb import obb
from langchain.tools import Tool

def get_stock_price(ticker: str) -> str:
    """Get the current stock price for a given ticker."""
    try:
        data = obb.equity.price.quote(symbol=ticker)
        return f"The current price of {ticker} is ${data['Price']:.2f}"
    except Exception as e:
        return f"Error fetching stock price for {ticker}: {str(e)}"

def get_company_overview(ticker: str) -> str:
    """Get an overview of a company for a given ticker."""
    try:
        data = obb.equity.profile(symbol=ticker)
        return f"Overview of {ticker}:\n" \
               f"Sector: {data['Sector']}\n" \
               f"Industry: {data['Industry']}\n" \
               f"Market Cap: ${data['MarketCapitalization']:,}\n" \
               f"52-Week High: ${data['52WeekHigh']:.2f}\n" \
               f"52-Week Low: ${data['52WeekLow']:.2f}"
    except Exception as e:
        return f"Error fetching company overview for {ticker}: {str(e)}"

# Create LangChain tools
tools = [
    Tool(
        name="StockPrice",
        func=get_stock_price,
        description="Useful for getting the current stock price of a company. Input should be a stock ticker symbol."
    ),
    Tool(
        name="CompanyOverview",
        func=get_company_overview,
        description="Useful for getting an overview of a company. Input should be a stock ticker symbol."
    )
]