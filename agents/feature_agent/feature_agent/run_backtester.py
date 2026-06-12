import os
import math
from datetime import date, timedelta
import pandas as pd
import yfinance as yf

def run_portfolio_backtest(ticker_string: str, quarter_end_date: str, hold_days: int = 365) -> pd.DataFrame:
    """
    Takes a space-separated string of tickers from the agent, simulates buying them 
    on the 45-day SEC disclosure lag date, and calculates a 1-year hold return.
    """
    # 1. Parse tickers into a clean list
    tickers = list(set(ticker_string.split()))
    if not tickers:
        print("❌ No tickers provided for backtesting.")
        return pd.DataFrame()

    # 2. Calculate execution window (Start date is Q-End + 45 days)
    start_dt = date.fromisoformat(quarter_end_date) + timedelta(days=45)
    end_dt = start_dt + timedelta(days=hold_days)

    print(f"📊 Running {hold_days}-Day Buy-and-Hold Audit for {len(tickers)} assets...")
    print(f"  - Entry Date (SEC Disclosure Lag): {start_dt}")
    print(f"  - Exit Date: {end_dt}")

    # 3. Download the historical pricing batch (with a safety buffer for weekends)
    data = yf.download(
        tickers, 
        start=start_dt, 
        end=end_dt + timedelta(days=10), 
        group_by='ticker', 
        progress=False, 
        auto_adjust=True, 
        threads=True
    )

    results = []

    # 4. Iterate through each asset and calculate standard buy-and-hold returns
    for ticker in tickers:
        try:
            t_data = data[ticker] if len(tickers) > 1 else data
            t_data = t_data.dropna(subset=['Close'])
            
            if t_data.empty or len(t_data) < 2:
                print(f"  - {ticker}: Skipping due to insufficient data footprints.")
                continue
                
            # Entry price on day 1 of disclosure; exit price exactly at the end of the holding block
            entry_p = float(t_data['Close'].iloc[0])
            exit_p = float(t_data['Close'].iloc[-1])
            
            if not math.isnan(entry_p) and not math.isnan(exit_p):
                roi = round(((exit_p - entry_p) / entry_p) * 100, 2)
                results.append({
                    "Ticker": ticker,
                    "Entry Price": round(entry_p, 2),
                    "Exit Price": round(exit_p, 2),
                    "Return %": roi
                })
        except Exception as e:
            print(f"  - {ticker}: Error processing returns - {e}")
            continue

    # 5. Compile dataframe and calculate high-level portfolio statistics
    df_results = pd.DataFrame(results)
    if not df_results.empty:
        avg_roi = df_results["Return %"].mean()
        win_rate = (df_results["Return %"] > 0).sum() / len(df_results) * 100
        
        print("\n==================================================")
        print("📊 PORTFOLIO BACKTEST PERFORMANCE")
        print("==================================================")
        print(f"Average Portfolio ROI : {avg_roi:.2f}%")
        print(f"Portfolio Win Rate    : {win_rate:.2f}%")
        print("==================================================\n")
        
        return df_results.sort_values(by="Return %", ascending=False)
    
    return df_results

# =====================================================================
# EXECUTION WORKFLOW
# =====================================================================
if __name__ == "__main__":
    # 1. Paste the exact space-separated ticker output your agent gave you for 2024
    # (Example snippet from your 2024 results payload)
    agent_output_tickers = "META JPM XOM V MA COST PG BABA JNJ XLE WMT UBER MELI ABBV PLTR GEV GE"
    
    # 2. Define the exact quarter-end baseline date
    target_quarter = "2024-12-31" 
    
    # 3. Execute the performance check (365 days hold)
    performance_table = run_portfolio_backtest(
        ticker_string=agent_output_tickers, 
        quarter_end_date=target_quarter,
        hold_days=365
    )
    
    # Display individual breakdown records
    print(performance_table.to_string(index=False))