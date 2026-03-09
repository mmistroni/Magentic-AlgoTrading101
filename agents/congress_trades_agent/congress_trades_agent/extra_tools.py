import json

def fetch_form4_signals_tool(ticker: str, analysis_date: str):
    """
    Insider Alignment Validator: Retrieves recent Form 4 insider trading data (CEOs, Directors) for a specific ticker.
    
    Use this tool to check for 'The Triple Crown' (Congress + Corporate Lobbying + C-Suite Insiders all aligning).
    It uses mocked data for backtesting purposes.

    Args:
        ticker (str): The stock symbol (e.g., 'BE', 'MOH', 'NDAQ').
        analysis_date (str): The reference date in 'YYYY-MM-DD' format.

    Returns:
        str: A JSON string containing insider transaction details:
             - 'insider_title': Role of the insider (e.g., 'CEO', 'CFO').
             - 'transaction_type': 'Buy' or 'Sell'.
             - 'shares': Number of shares transacted.
             - 'transaction_date': When the trade occurred.
             - 'signal_strength': 'Strong', 'Neutral', or 'Warning'.
    """
    print(f"🕵️ Checking Form 4 Insider trades for: {ticker} around {analysis_date}")
    
    # Mocked database for our test cases
    mock_form4_db = {
        "BE": {
            "ticker": "BE",
            "insider_title": "CEO", 
            "transaction_type": "Buy", 
            "shares": 25000, 
            "transaction_date": "2024-10-25",
            "signal_strength": "Strong Buy Confluence"
        },
        "MOH": {
            "ticker": "MOH",
            "insider_title": "CFO", 
            "transaction_type": "Sell", 
            "shares": 15000, 
            "transaction_date": "2024-06-05",
            "signal_strength": "Warning - Insider Dumping"
        },
        "NDAQ": {
            "ticker": "NDAQ",
            "insider_title": "Director", 
            "transaction_type": "Hold", 
            "shares": 0, 
            "transaction_date": "N/A",
            "signal_strength": "Neutral"
        }
    }
    
    # Fetch data or return a default empty state if ticker not in mock DB
    insider_data = mock_form4_db.get(ticker.upper(), {
        "ticker": ticker,
        "error": "No recent insider transactions found.",
        "signal_strength": "Neutral"
    })
    
    return json.dumps(insider_data)