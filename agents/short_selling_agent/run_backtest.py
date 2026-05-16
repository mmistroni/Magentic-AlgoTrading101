import json
import os
import requests
import argparse
from datetime import datetime, timedelta

def get_fmp_key():
    key = os.environ.get("FMP_API_KEY")
    if not key:
        raise ValueError("Please set the FMP_API_KEY environment variable.")
    return key

def run_backtest(initial_capital=10000.0):
    print(f"🔄 Flipped Strategy: LONG MEAN REVERSION ENGINE")
    print(f"Filters -> Min Price: $5.00 | Entry: Day 1 Open LONG | Stop: 5% | Target: 8%")
    print(f"Starting Portfolio Capital: ${initial_capital:,.2f}\n")
    
    try:
        with open("signals.json", "r") as f:
            signals = json.load(f)
    except FileNotFoundError:
        print("❌ signals.json not found.")
        return

    api_key = get_fmp_key()
    signals.sort(key=lambda x: x["date"])
    
    current_capital = initial_capital
    winning_trades = 0
    total_trades = 0
    pnl_percentages = []
    active_positions = {}

    for signal in signals:
        ticker = signal["ticker"]
        entry_date_str = signal["date"]
        score = float(signal.get("conviction_score", 8))
        
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d")
        active_positions = {t: exp for t, exp in active_positions.items() if exp > entry_date}
        
        if ticker in active_positions:
            continue 
            
        # Give it a 7-day window to play out the bounce
        max_exit_date = entry_date + timedelta(days=7)
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={entry_date_str}&to={max_exit_date.strftime('%Y-%m-%d')}&apikey={api_key}"
        
        try:
            res = requests.get(url).json()
            historical = res.get("historical", [])
            if len(historical) < 2: 
                continue
                
            historical.reverse() 
            
            day_0_close = historical[0]["close"]
            
            # --- FILTER: EXCLUDE PENNY STOCKS LESS THAN $5 ---
            if day_0_close < 5.0:
                continue

            # --- THE FLIPPED EXECUTION (LONG ENTRY) ---
            # We buy the Open of Day 1 immediately following the crash
            day_1_open = historical[1]["open"]
            entry_price = day_1_open
            
            # Fixed, disciplined risk parameters for a long scalp
            stop_loss_pct = 5.0    # Tight 5% floor
            take_profit_pct = 8.0  # 8% target bounce
            
            stop_loss_price = entry_price * (1 - (stop_loss_pct / 100.0))
            take_profit_price = entry_price * (1 + (take_profit_pct / 100.0))
            
            # Baseline 3% capital sizing per setup
            conviction_modifier = score / 8.0
            allocated_capital = current_capital * 0.03 * conviction_modifier

            trade_closed = False
            actual_pnl_pct = 0.0
            actual_exit_date = max_exit_date
            
            # Watch Day 1 and subsequent days for the snap-back
            for idx, day in enumerate(historical[1:], start=1):
                daily_open = day["open"]
                daily_high = day["high"]
                daily_low = day["low"]
                daily_close = day["close"]
                current_bar_date = datetime.strptime(day["date"], "%Y-%m-%d")
                
                # 1. Check if the asset gaps down past our stop at the open
                if daily_open <= stop_loss_price:
                    actual_pnl_pct = ((daily_open - entry_price) / entry_price) * 100
                    print(f"[{entry_date_str}] {ticker}: 📉 GAP DOWN STOP OUT ({actual_pnl_pct:.2f}%)")
                    trade_closed = True
                    actual_exit_date = current_bar_date
                    break
                
                # 2. Check Intraday Stop Loss
                elif daily_low <= stop_loss_price:
                    actual_pnl_pct = -stop_loss_pct
                    print(f"[{entry_date_str}] {ticker}: ❌ STOP LOSS HIT (-{stop_loss_pct:.2f}%)")
                    trade_closed = True
                    actual_exit_date = current_bar_date
                    break
                    
                # 3. Check Intraday Take Profit (The Rubber-Band Snap)
                elif daily_high >= take_profit_price:
                    exit_p = max(take_profit_price, daily_open)
                    actual_pnl_pct = ((exit_p - entry_price) / entry_price) * 100
                    print(f"[{entry_date_str}] {ticker}: 🎉 BOUNCE WIN (+{actual_pnl_pct:.2f}%)")
                    winning_trades += 1
                    trade_closed = True
                    actual_exit_date = current_bar_date
                    break

            # If the trade is just grinding flat, exit at the end of the data window
            if not trade_closed:
                final_price = historical[-1]["close"]
                actual_pnl_pct = ((final_price - entry_price) / entry_price) * 100
                if actual_pnl_pct > 0:
                    print(f"[{entry_date_str}] {ticker}: ⏳ TIME EXIT WIN (+{actual_pnl_pct:.2f}%)")
                    winning_trades += 1
                else:
                    print(f"[{entry_date_str}] {ticker}: ⏳ TIME EXIT LOSS ({actual_pnl_pct:.2f}%)")
                actual_exit_date = max_exit_date

            # Process Long Capital Accounting
            trade_dollar_return = allocated_capital * (actual_pnl_pct / 100.0)
            current_capital += trade_dollar_return
            pnl_percentages.append(actual_pnl_pct)
            total_trades += 1
            active_positions[ticker] = actual_exit_date
            
        except Exception as e:
            pass

    print("\n" + "=" * 50)
    print("🏆 LONG MEAN REVERSION RESULTS")
    print(f"Total Trades Taken: {total_trades}")
    if total_trades > 0:
        print(f"Win Rate: {(winning_trades / total_trades) * 100:.1f}%")
        print(f"Average Profit Per Trade: {sum(pnl_percentages) / total_trades:.2f}%")
        print(f"Final Account Balance: ${current_capital:,.2f} ({((current_capital - initial_capital)/initial_capital)*100:.2f}% Net Return)")
    print("=" * 50)

if __name__ == "__main__":
    run_backtest()