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

def run_backtest(max_hold_days=15, initial_capital=10000.0):
    print(f"🚀 ULTIMATE REFINED SHORT ENGINE")
    print(f"Filters -> Min Price: $5.00 | Entry: 2-Day Calm Filter | Target Cap: $200/mo")
    print(f"Initial Portfolio Capital: ${initial_capital:,.2f}\n")
    
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

    # Monthly signal counter to adjust sizing dynamically based on volume regime
    from collections import Counter
    months = [s["date"][:7] for s in signals]
    monthly_counts = Counter(months)
    
    # Track monthly performance to enforce the $200 stop-trading cap
    monthly_profits = {}

    for signal in signals:
        ticker = signal["ticker"]
        entry_date_str = signal["date"]
        score = float(signal.get("conviction_score", 8))
        current_month = entry_date_str[:7]
        
        entry_date = datetime.strptime(entry_date_str, "%Y-%m-%d")
        active_positions = {t: exp for t, exp in active_positions.items() if exp > entry_date}
        
        if ticker in active_positions:
            continue 
            
        # --- RULE: AUTOMATIC MONTHLY PROFIT LOCK ($200 CAP) ---
        if monthly_profits.get(current_month, 0.0) >= 200.0:
            # We already hit your $200 target for this calendar month. Freeze trading!
            continue

        max_exit_date = entry_date + timedelta(days=max_hold_days)
        url = f"https://financialmodelingprep.com/api/v3/historical-price-full/{ticker}?from={entry_date_str}&to={max_exit_date.strftime('%Y-%m-%d')}&apikey={api_key}"
        
        try:
            res = requests.get(url).json()
            historical = res.get("historical", [])
            if len(historical) < 3: # Need at least 3 bars to evaluate 2-day delay rules safely
                continue
                
            historical.reverse() 
            
            day_0_close = historical[0]["close"]
            
            # --- FILTER: EXCLUDE PENNY STOCKS LESS THAN $5 ---
            if day_0_close < 5.0:
                continue

            day_0_open = historical[0]["open"]
            day_0_drop = abs((day_0_close - day_0_open) / day_0_open) if day_0_open else 0.20
            if day_0_drop < 0.10: 
                day_0_drop = 0.20
            
            # Risk Brackets
            stop_loss_pct = day_0_drop * 0.5 * 100    
            take_profit_pct = day_0_drop * 0.75 * 100 
            
            # Sizing Modifiers
            total_signals_this_month = monthly_counts[current_month]
            if total_signals_this_month <= 10:
                base_capital_risk = 0.06  
            else:
                base_capital_risk = 0.025 
                
            conviction_modifier = score / 8.0
            allocated_capital = current_capital * base_capital_risk * conviction_modifier

            trade_entered = False
            trade_closed = False
            entry_price = 0.0
            stop_loss_price = 0.0
            take_profit_price = 0.0
            days_since_entry = 0
            actual_pnl_pct = 0.0
            actual_exit_date = max_exit_date
            
            # Walk forward through data bars starting Day 1 onwards
            for idx, day in enumerate(historical[1:], start=1):
                daily_open = day["open"]
                daily_high = day["high"]
                daily_low = day["low"]
                daily_close = day["close"]
                current_bar_date = datetime.strptime(day["date"], "%Y-%m-%d")
                
                # --- STEP 1: THE 2-DAY CALM ENTRY FILTER ---
                if not trade_entered:
                    if idx < 2: 
                        continue # Completely step aside and ignore Day 1's volatile bounce
                    
                    # On Day 2, we execute only if the asset is calmly holding below the Day 0 baseline
                    if daily_open <= day_0_close * 1.02:
                        entry_price = daily_open
                        trade_entered = True
                        stop_loss_price = entry_price * (1 + (stop_loss_pct / 100.0))
                        take_profit_price = entry_price * (1 - (take_profit_pct / 100.0))
                    else:
                        break # Price is squeezing aggressively upwards; abandon signal safely
                    continue

                # --- STEP 2: ACTIVE POSITION MANAGEMENT ---
                days_since_entry += 1
                
                # Opening Gap-Up Defense
                if daily_open >= stop_loss_price:
                    actual_pnl_pct = ((entry_price - daily_open) / entry_price) * 100
                    print(f"[{entry_date_str}] {ticker}: 💥 GAP STOPPED OUT ({actual_pnl_pct:.2f}%)")
                    trade_closed = True
                    actual_exit_date = current_bar_date
                    break
                    
                # Intraday Stop Loss Risk
                elif daily_high >= stop_loss_price:
                    actual_pnl_pct = -stop_loss_pct
                    print(f"[{entry_date_str}] {ticker}: ❌ INTRADAY STOP LOSS (-{stop_loss_pct:.2f}%)")
                    trade_closed = True
                    actual_exit_date = current_bar_date
                    break
                    
                # Intraday Take Profit Target
                elif daily_low <= take_profit_price:
                    exit_p = min(take_profit_price, daily_open)
                    actual_pnl_pct = ((entry_price - exit_p) / entry_price) * 100
                    print(f"[{entry_date_str}] {ticker}: ✅ WIN (+{actual_pnl_pct:.2f}%)")
                    winning_trades += 1
                    trade_closed = True
                    actual_exit_date = current_bar_date
                    break
                    
                # --- STEP 3: 5-DAY STALL MOMENTUM KILL SWITCH ---
                elif days_since_entry == 5: 
                    current_pnl = ((entry_price - daily_close) / entry_price) * 100
                    if current_pnl < 0:
                        actual_pnl_pct = current_pnl
                        print(f"[{entry_date_str}] {ticker}: ⏳ 5-DAY MOMENTUM CUT (Closed at {actual_pnl_pct:.2f}%)")
                        trade_closed = True
                        actual_exit_date = current_bar_date
                        break
                    else:
                        # Protect open profits with a sliding floor trailing stop buffer
                        stop_loss_price = entry_price * (1 + ((stop_loss_pct * 0.35) / 100.0))

            # Terminal Boundary Resolution
            if trade_entered and not trade_closed:
                final_price = historical[-1]["close"]
                actual_pnl_pct = ((entry_price - final_price) / entry_price) * 100
                if actual_pnl_pct > 0:
                    print(f"[{entry_date_str}] {ticker}: ⏳ TIME STOP WIN (+{actual_pnl_pct:.2f}%)")
                    winning_trades += 1
                else:
                    print(f"[{entry_date_str}] {ticker}: ⏳ TIME STOP LOSS ({actual_pnl_pct:.2f}%)")
                actual_exit_date = max_exit_date

            # Process capital accounting updates
            if trade_entered:
                trade_dollar_return = allocated_capital * (actual_pnl_pct / 100.0)
                current_capital += trade_dollar_return
                pnl_percentages.append(actual_pnl_pct)
                total_trades += 1
                active_positions[ticker] = actual_exit_date
                
                # Log monthly delta progression
                monthly_profits[current_month] = monthly_profits.get(current_month, 0.0) + trade_dollar_return
            
        except Exception as e:
            pass

    print("\n" + "=" * 50)
    print("🏆 REFINED BACKTEST COMPLETE")
    print(f"Total Trades Taken: {total_trades}")
    if total_trades > 0:
        print(f"Win Rate: {(winning_trades / total_trades) * 100:.1f}%")
        print(f"Average Profit Per Trade: {sum(pnl_percentages) / total_trades:.2f}%")
        print(f"Final Account Balance: ${current_capital:,.2f} ({((current_capital - initial_capital)/initial_capital)*100:.2f}% Net Return)")
    print("=" * 50)

if __name__ == "__main__":
    run_backtest()