import pandas as pd
import yfinance as yf
from datetime import datetime, timedelta

# 1. Your Agent's Recommendations
trades = [
    {"date": "2025-02-01", "ticker": "JPM", "action": "BUY"},
    {"date": "2025-02-01", "ticker": "FCFS", "action": "BUY"},
    {"date": "2025-06-01", "ticker": "MKL", "action": "BUY"},
    {"date": "2025-06-01", "ticker": "NVT", "action": "BUY"},
    {"date": "2025-11-01", "ticker": "FIG", "action": "BUY"} 
]

def calculate_portfolio_returns(trade_list):
    results = []
    
    print(f"{'TICKER':<10} {'ENTRY':<12} {'EXIT (6M)':<12} {'RETURN':<10} {'RESULT'}")
    print("-" * 60)

    for trade in trade_list:
        if trade['action'] != 'BUY': continue
        
        ticker = trade['ticker']
        start_date = pd.to_datetime(trade['date'])
        
        # Calculate Exit Date (6 Months later)
        end_date = start_date + pd.DateOffset(months=6)
        
        # Cap the exit date if your data ends in Feb 2026
        max_date = pd.to_datetime("2026-02-01")
        if end_date > max_date:
            end_date = max_date # Close trade at end of simulation

        try:
            # ---------------------------------------------------------
            # ROBUST PRICE LOOKUP (Replaces the commented block)
            # ---------------------------------------------------------
            
            # Fetch slightly wider window to handle weekends
            data = yf.download(ticker, start=start_date, end=end_date + timedelta(days=5), progress=False)
            
            if data.empty:
                print(f"⚠️ No data found for {ticker} (Likely delisted/renamed)")
                continue

            # Ensure we are using 'Adj Close' to account for dividends/splits
            # If MultiIndex columns (common in new yfinance), flatten or select correctly
            if isinstance(data.columns, pd.MultiIndex):
                close_prices = data['Close'][ticker]
            else:
                close_prices = data['Close']

            # Find First Valid Price on or after Start Date
            entry_row = close_prices[close_prices.index >= start_date]
            if entry_row.empty:
                print(f"⚠️ No entry price found for {ticker}")
                continue
            entry_price = float(entry_row.iloc[0]) # Force float

            # Find Last Valid Price on or before End Date
            exit_row = close_prices[close_prices.index <= end_date]
            if exit_row.empty:
                print(f"⚠️ No exit price found for {ticker}")
                continue
            exit_price = float(exit_row.iloc[-1]) # Force float
            
            # Calculate Return
            pct_change = ((exit_price - entry_price) / entry_price) * 100
            outcome = "✅ WIN" if pct_change > 0 else "❌ LOSS"
            if pct_change > 20: outcome = "🚀 MOON"

            print(f"{ticker:<10} {entry_price:<12.2f} {exit_price:<12.2f} {pct_change:+.2f}%    {outcome}")
            
            results.append(pct_change)

        except Exception as e:
            print(f"Error data for {ticker}: {e}")

    print("-" * 60)
    avg_return = sum(results) / len(results)
    print(f"💰 AVERAGE PORTFOLIO RETURN: {avg_return:.2f}%")

if __name__ == "__main__":
    calculate_portfolio_returns(trades)
