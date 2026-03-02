import yfinance as yf
import pandas as pd

def analyze_abbv_trade():
    print("🕵️  Analyzing ABBV Political Alpha (Aug 2025 - Mar 2026)")
    
    trade_date = "2025-08-21"
    lobby_date = "2025-10-09"
    exit_date  = "2026-03-01"

    print(f"📥 Fetching ABBV data...")
    ticker = "ABBV"
    try:
        df = yf.download(ticker, start="2025-08-01", end="2026-03-02", progress=False)
        
        if df.empty:
            print("❌ No data found.")
            return
            
        def get_price(target_date):
            target_dt = pd.to_datetime(target_date)
            idx = df.index.get_indexer([target_dt], method='nearest')[0]
            actual_date = df.index[idx]
            # FIX: Ensure we extract the scalar value
            price = df.iloc[idx]['Close'].item() 
            return actual_date, price

        t_date, t_price = get_price(trade_date)
        l_date, l_price = get_price(lobby_date)
        e_date, e_price = get_price(exit_date)

        initial_return = ((l_price - t_price) / t_price) * 100
        total_return = ((e_price - t_price) / t_price) * 100

        print("\n📊 TRADE PERFORMANCE REPORT")
        print("===========================")
        print(f"🔹 Entry (Senator Buy):  {t_date.date()} @ ${t_price:.2f}")
        print(f"🔹 Event (Lobbying):     {l_date.date()} @ ${l_price:.2f}")
        print(f"🔹 Current (March '26):  {e_date.date()} @ ${e_price:.2f}")
        print("---------------------------")
        print(f"🚀 Return at Lobbying:   {initial_return:+.2f}%")
        print(f"💰 Total Return (Today): {total_return:+.2f}%")
        
        # ... rest of your logic
    except Exception as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    analyze_abbv_trade()