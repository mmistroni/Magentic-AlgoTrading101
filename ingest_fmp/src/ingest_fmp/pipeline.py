import os
import time
import logging
import pandas as pd
from ingest_fmp.client import FMPClient
from ingest_fmp.screeners import StockScreeners
from ingest_fmp.fundamental_validator import FundamentalValidator, MarketDownFundamentalValidator
from ingest_fmp.technical_validator import TechnicalValidator, BearishTechnicalValidator

logger = logging.getLogger(__name__)

def get_extra_watchlist(limit: int = None) -> list[dict]:
    start_time = time.time()
    print("⏱️ [Extra Watchlist] Starting pipeline execution...", flush=True)
    
    client = FMPClient()
    
    # --- Step 1: Direct FMP Descriptive Screener Call ---
    print("📡 [Extra Watchlist] Step 1: Requesting descriptive screener data from FMP...", flush=True)
    desc_params = {
        "marketCapMoreThan": 2000000000,    # Mid cap over $2B
        "priceMoreThan": 10,               # Price over $10
        "avgVolumeMoreThan": 200000,       # Average volume over 200K
        "country": "US",                   # US markets only
        "isEtf": "false",                  # Exclude ETFs
        "isFund": "false",                 # Exclude Funds
        "isActivelyTrading": "true",       # Actively trading equities
        "limit": 1000
    }
    
    raw_data = client.get_company_screener(desc_params)
    if not raw_data:
        print("⚠️ [Extra Watchlist] No data returned from FMP screener.", flush=True)
        return []

    df = pd.DataFrame(raw_data)
    if "symbol" in df.columns:
        df = df.dropna(subset=["symbol"])

    candidates = df.to_dict(orient="records")
    print(f"📊 [Extra Watchlist] Retrieved {len(candidates)} raw candidates.", flush=True)
    
    # Stamp strategy metadata onto each record bag
    for candidate in candidates:
        candidate["strategy_name"] = "extra_watchlist"
        candidate["timestamp"] = pd.Timestamp.utcnow().isoformat()

    # --- Step 2: Fundamental Enrichment & Validation ---
    print("🔬 [Extra Watchlist] Step 2: Running fundamental validation...", flush=True)
    fund_validator = FundamentalValidator(client=client)
    fundamentally_sound = []
    
    for i, candidate in enumerate(candidates):
        if i > 0 and i % 20 == 0:
            print(f"⏳ [Extra Watchlist] Fundamental progress: {i}/{len(candidates)}...", flush=True)
        try:
            result = fund_validator.evaluate(candidate)
            if result:
                fundamentally_sound.append(result)
        except Exception:
            continue

    print(f"✅ [Extra Watchlist] {len(fundamentally_sound)} symbols passed fundamental checks.", flush=True)

    # --- Step 3: Technical Enrichment & Validation ---
    print("📈 [Extra Watchlist] Step 3: Running technical validation...", flush=True)
    tech_validator = TechnicalValidator(client=client)
    final_watchlist = []
    
    for i, candidate in enumerate(fundamentally_sound):
        if i > 0 and i % 10 == 0:
            print(f"⏳ [Extra Watchlist] Technical progress: {i}/{len(fundamentally_sound)}...", flush=True)
        try:
            result = tech_validator.evaluate(candidate)
            if result:
                final_watchlist.append(result)
        except Exception:
            continue

    elapsed = time.time() - start_time
    print(f"✨ [Extra Watchlist] Pipeline complete in {elapsed:.2f} seconds. Final records: {len(final_watchlist)}", flush=True)
    return final_watchlist


def run_market_down_pipeline(limit: int = None) -> list:
    start_time = time.time()
    print("⏱️ [Market Down] Starting pipeline execution...", flush=True)
    
    client = FMPClient()
    market_down_params = {
        "exchange": "NASDAQ",
        "marketCapMoreThan": 2000000000,  # Mid cap over $2B
        "country": "US",
        "isActivelyTrading": "true",
        "limit": limit if limit is not None else 1000
    }
    
    print("📡 [Market Down] Step 1: Fetching descriptive universe...", flush=True)
    raw_data = client.get_company_screener(market_down_params)

    if not raw_data:
        print("⚠️ [Market Down] No data returned for descriptive screener.", flush=True)
        return []

    df = pd.DataFrame(raw_data)
    
    if "shortFloat" in df.columns:
        df = df[df["shortFloat"] > 0.20]
        
    if "symbol" not in df.columns:
        return []
        
    symbols = df["symbol"].tolist()
    print(f"📊 [Market Down] Descriptive universe secured: {len(symbols)} tickers.", flush=True)

    # 2. Fundamentals (Negative EPS)
    print("🔬 [Market Down] Step 2: Fundamental validation (Negative EPS)...", flush=True)
    fund_validator = MarketDownFundamentalValidator(client)
    filtered_funds = []
    for i, sym in enumerate(symbols):
        if i > 0 and i % 20 == 0:
            print(f"⏳ [Market Down] Fundamental progress: {i}/{len(symbols)}...", flush=True)
        try:
            if fund_validator.evaluate({"symbol": sym}):
                filtered_funds.append(sym)
        except Exception:
            continue
            
    print(f"✅ [Market Down] {len(filtered_funds)} tickers passed fundamental checks.", flush=True)

    # 3. Technicals (Price < SMA20)
    print("📉 [Market Down] Step 3: Technical validation (Price < SMA20)...", flush=True)
    tech_validator = BearishTechnicalValidator(client)
    final_results = []
    for i, sym in enumerate(filtered_funds):
        if i > 0 and i % 10 == 0:
            print(f"⏳ [Market Down] Technical progress: {i}/{len(filtered_funds)}...", flush=True)
        try:
            if tech_validator.evaluate({"symbol": sym}):
                final_results.append(sym)
        except Exception:
            continue

    elapsed = time.time() - start_time
    print(f"✨ [Market Down] Pipeline complete in {elapsed:.2f} seconds. Final watchlist: {final_results}", flush=True)
    return final_results


def run_high_growth_float_watchlist(limit: int = None) -> list:
    start_time = time.time()
    print("⏱️ [High Growth Float] Starting pipeline execution...", flush=True)
    
    client = FMPClient()
    
    print("📡 [High Growth Float] Step 1: Descriptive screener & float filtering...", flush=True)
    base_params = {
        "priceMoreThan": 5,
        "avgVolumeMoreThan": 200000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": limit if limit is not None else 1000
    }
    
    raw_data = client.get_company_screener(base_params)
    if not raw_data:
        print("⚠️ [High Growth Float] No data returned from screener.", flush=True)
        return []

    df = pd.DataFrame(raw_data)
    
    if "floatShares" in df.columns:
        df = df[df["floatShares"] < 50000000]
        
    symbols = df["symbol"].tolist() if "symbol" in df.columns else []
    print(f"📊 [High Growth Float] Filtered down to {len(symbols)} candidates after float check.", flush=True)

    print("🔬 [High Growth Float] Step 2: Fundamental validation...", flush=True)
    validator = FundamentalValidator(
        client=client,
        min_eps_growth=0.20,
        min_roe=0.15,
        min_gross_margin=0.0,
        max_institutional_ownership=0.80
    )

    final_watchlist = []
    for i, sym in enumerate(symbols):
        if i > 0 and i % 20 == 0:
            print(f"⏳ [High Growth Float] Progress: {i}/{len(symbols)}...", flush=True)
        try:
            if validator.evaluate({"symbol": sym}):
                final_watchlist.append(sym)
        except Exception:
            continue

    elapsed = time.time() - start_time
    print(f"✨ [High Growth Float] Pipeline complete in {elapsed:.2f} seconds. Final watchlist: {final_watchlist}", flush=True)
    return final_watchlist


def run_swing_trading_pipeline(limit: int = None) -> list:
    start_time = time.time()
    print("⏱️ [Swing Trading] Starting pipeline execution...", flush=True)
    
    client = FMPClient()
    
    print("📡 [Swing Trading] Step 1: Descriptive filters...", flush=True)
    base_params = {
        "priceMoreThan": 10,
        "avgVolumeMoreThan": 200000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": limit if limit is not None else 1000
    }
    
    raw_data = client.get_company_screener(base_params)
    if not raw_data:
        print("⚠️ [Swing Trading] No data returned for screener.", flush=True)
        return []

    df = pd.DataFrame(raw_data)
    
    if "relativeVolume" in df.columns:
        df = df[df["relativeVolume"] > 1.5]

    symbols = df["symbol"].tolist() if "symbol" in df.columns else []
    print(f"📊 [Swing Trading] Screened {len(symbols)} candidates. Checking 52-week high via quotes...", flush=True)

    # --- Step 1b: Quote Filtering ---
    quote_filtered_symbols = []
    for i, symbol in enumerate(symbols):
        if i > 0 and i % 50 == 0:
            print(f"⏳ [Swing Trading] Quote check progress: {i}/{len(symbols)}...", flush=True)
        try:
            quote_data = client.get_quote(symbol)
            if not quote_data:
                continue
            q = quote_data[0]
            price = q.get("price", 0)
            year_high = q.get("yearHigh", 0)
            
            if year_high and price <= year_high * 0.95:
                quote_filtered_symbols.append(symbol)
        except Exception:
            continue

    print(f"✅ [Swing Trading] {len(quote_filtered_symbols)} candidates passed 52-week high check.", flush=True)

    # --- Step 2: Fundamental Validation ---
    print("🔬 [Swing Trading] Step 2: Fundamental validation...", flush=True)
    fund_validator = FundamentalValidator(
        client=client,
        min_eps_growth=0.0,
        min_roe=0.0,
        min_gross_margin=0.0,
        max_institutional_ownership=0.60
    )

    fundamentally_sound = []
    for i, sym in enumerate(quote_filtered_symbols):
        if i > 0 and i % 20 == 0:
            print(f"⏳ [Swing Trading] Fundamental progress: {i}/{len(quote_filtered_symbols)}...", flush=True)
        try:
            if fund_validator.evaluate({"symbol": sym}):
                fundamentally_sound.append(sym)
        except Exception:
            continue

    print(f"✅ [Swing Trading] {len(fundamentally_sound)} symbols passed fundamental checks.", flush=True)

    # --- Step 3: Technical Validation ---
    print("📈 [Swing Trading] Step 3: Technical validation...", flush=True)
    tech_validator = TechnicalValidator(client)
    final_watchlist = []
    
    for i, sym in enumerate(fundamentally_sound):
        if i > 0 and i % 10 == 0:
            print(f"⏳ [Swing Trading] Technical progress: {i}/{len(fundamentally_sound)}...", flush=True)
        try:
            if tech_validator.evaluate({"symbol": sym}):
                final_watchlist.append(sym)
        except Exception:
            continue

    elapsed = time.time() - start_time
    print(f"✨ [Swing Trading] Pipeline complete in {elapsed:.2f} seconds. Final watchlist: {final_watchlist}", flush=True)
    return final_watchlist


def run_new_highs_pipeline(limit: int = None) -> list:
    start_time = time.time()
    print("⏱️ [New Highs] Starting pipeline execution...", flush=True)
    
    client = FMPClient()
    
    print("📡 [New Highs] Step 1: Descriptive filters...", flush=True)
    base_params = {
        "marketCapMoreThan": 300000000,
        "priceMoreThan": 10,
        "avgVolumeMoreThan": 200000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": limit if limit is not None else 1000
    }
    
    raw_data = client.get_company_screener(base_params)
    if not raw_data:
        print("⚠️ [New Highs] No data returned for screener.", flush=True)
        return []

    df = pd.DataFrame(raw_data)
    
    if "relativeVolume" in df.columns:
        df = df[df["relativeVolume"] > 1.0]

    symbols = df["symbol"].tolist() if "symbol" in df.columns else []
    print(f"📊 [New Highs] Screened {len(symbols)} candidates. Evaluating live quotes & 52-week highs...", flush=True)

    # --- Step 1b: Quote & New High Filtering ---
    new_high_candidates = []
    for i, symbol in enumerate(symbols):
        if i > 0 and i % 50 == 0:
            print(f"⏳ [New Highs] Quote check progress: {i}/{len(symbols)}...", flush=True)
        try:
            quote_data = client.get_quote(symbol)
            if not quote_data:
                continue
            q = quote_data[0]
            price = q.get("price", 0)
            open_price = q.get("open", 0)
            prev_close = q.get("previousClose", 0)
            year_high = q.get("yearHigh", 0)
            
            if year_high and price and open_price and prev_close:
                if price > prev_close and price > open_price and price >= year_high * 0.99:
                    new_high_candidates.append(symbol)
        except Exception:
            continue

    print(f"✅ [New Highs] {len(new_high_candidates)} candidates met New High criteria.", flush=True)

    # --- Step 2: Fundamental Validation ---
    print("🔬 [New Highs] Step 2: Fundamental validation...", flush=True)
    fund_validator = FundamentalValidator(
        client=client,
        min_eps_growth=0.0,
        min_roe=0.0,
        min_gross_margin=0.0,
        max_institutional_ownership=0.60
    )

    fundamentally_sound = []
    for i, sym in enumerate(new_high_candidates):
        if i > 0 and i % 20 == 0:
            print(f"⏳ [New Highs] Fundamental progress: {i}/{len(new_high_candidates)}...", flush=True)
        try:
            if fund_validator.evaluate({"symbol": sym}):
                fundamentally_sound.append(sym)
        except Exception:
            continue

    print(f"✅ [New Highs] {len(fundamentally_sound)} symbols passed fundamental checks.", flush=True)

    # --- Step 3: Technical Validation ---
    print("📈 [New Highs] Step 3: Technical validation...", flush=True)
    tech_validator = TechnicalValidator(client)
    final_watchlist = []
    
    for i, sym in enumerate(fundamentally_sound):
        if i > 0 and i % 10 == 0:
            print(f"⏳ [New Highs] Technical progress: {i}/{len(fundamentally_sound)}...", flush=True)
        try:
            if tech_validator.evaluate({"symbol": sym}):
                final_watchlist.append(sym)
        except Exception:
            continue

    elapsed = time.time() - start_time
    print(f"✨ [New Highs] Pipeline complete in {elapsed:.2f} seconds. Final watchlist: {final_watchlist}", flush=True)
    return final_watchlist


def run_eod_screener(limit: int = None) -> list:
    start_time = time.time()
    print("⏱️ [EOD Screener] Starting pipeline execution...", flush=True)
    
    client = FMPClient()
    
    print("📡 [EOD Screener] Step 1: Requesting descriptive screener data from FMP...", flush=True)
    base_params = {
        "priceMoreThan": 10,
        "avgVolumeMoreThan": 200000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": limit if limit is not None else 1000
    }
    
    raw_data = client.get_company_screener(base_params)
    if not raw_data:
        print("⚠️ [EOD Screener] No data returned from FMP screener.", flush=True)
        return []

    df = pd.DataFrame(raw_data)
    print(f"📊 [EOD Screener] Fetched {len(df)} raw symbols from FMP screener.", flush=True)
    
    if "relativeVolume" in df.columns:
        df = df[df["relativeVolume"] > 1.5]
        print(f"🔍 [EOD Screener] {len(df)} symbols passed Relative Volume > 1.5 filter.", flush=True)

    symbols = df["symbol"].tolist() if "symbol" in df.columns else []

    # --- Step 1b: Quote Filtering ---
    print(f"📡 [EOD Screener] Step 1b: Fetching quotes for {len(symbols)} candidates (52-week high check)...", flush=True)
    quote_filtered_symbols = []
    for i, symbol in enumerate(symbols):
        if i > 0 and i % 50 == 0:
            print(f"⏳ [EOD Screener] Progress: Processed quotes for {i}/{len(symbols)} symbols...", flush=True)
        
        try:
            quote_data = client.get_quote(symbol)
            if not quote_data:
                continue
            q = quote_data[0]
            price = q.get("price", 0)
            year_high = q.get("yearHigh", 0)
            
            if year_high and price <= year_high * 0.95:
                quote_filtered_symbols.append(symbol)
        except Exception:
            continue

    print(f"✅ [EOD Screener] {len(quote_filtered_symbols)} symbols passed quote filtering.", flush=True)

    # --- Step 2: Fundamental Validation ---
    print("🔬 [EOD Screener] Step 2: Running fundamental validation...", flush=True)
    fund_validator = FundamentalValidator(
        client=client,
        min_eps_growth=0.0,
        min_roe=0.0,
        min_gross_margin=0.0,
        max_institutional_ownership=0.60
    )

    fundamentally_sound = []
    for i, symbol in enumerate(quote_filtered_symbols):
        if i > 0 and i % 20 == 0:
            print(f"⏳ [EOD Screener] Fundamental check progress: {i}/{len(quote_filtered_symbols)}...", flush=True)
        try:
            if fund_validator.evaluate({"symbol": symbol}):
                fundamentally_sound.append(symbol)
        except Exception:
            continue
            
    print(f"✅ [EOD Screener] {len(fundamentally_sound)} symbols passed fundamental checks.", flush=True)

    # --- Step 3: Technical Validation ---
    print("📈 [EOD Screener] Step 3: Running technical validation...", flush=True)
    tech_validator = TechnicalValidator(client)
    final_watchlist = []
    
    for i, symbol in enumerate(fundamentally_sound):
        if i > 0 and i % 10 == 0:
            print(f"⏳ [EOD Screener] Technical check progress: {i}/{len(fundamentally_sound)}...", flush=True)
        try:
            result = tech_validator.evaluate({"symbol": symbol})
            if result:
                result["strategy_name"] = "eod_screener"
                result["timestamp"] = pd.Timestamp.utcnow().isoformat()
                final_watchlist.append(result)
        except Exception:
            continue

    elapsed = time.time() - start_time
    print(f"✨ [EOD Screener] Pipeline complete in {elapsed:.2f} seconds. Final records: {len(final_watchlist)}", flush=True)
    return final_watchlist