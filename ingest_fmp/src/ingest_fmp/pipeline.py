import logging
import pandas as pd
from ingest_fmp.client import FMPClient
from ingest_fmp.screeners import StockScreeners
from ingest_fmp.fundamental_validator import FundamentalValidator, MarketDownFundamentalValidator
from ingest_fmp.technical_validator import TechnicalValidator, BearishTechnicalValidator

logger = logging.getLogger(__name__)

def get_extra_watchlist() -> list[dict]:
    """
    Orchestrates the Extra Watchlist Pipeline:
    1. Descriptive: Mid/Large Cap (> $2B), Price > $10, Avg Vol > 200K, Active US equities.
    2. Fundamental: Positive growth, institutional limits, or standard fundamental profiles.
    3. Technical: Bullish SMA alignment (Price > SMA20 > SMA50 > SMA200).
    4. Output: Fully enriched dictionaries ready for BigQuery insertion.
    """
    client = FMPClient()
    
    # --- Step 1: Direct FMP Descriptive Screener Call ---
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
    
    logger.info("Fetching extra watchlist universe directly via FMP client...")
    raw_data = client.get_company_screener(desc_params)
    if not raw_data:
        logger.warning("No data returned from FMP screener for Extra Watchlist.")
        return []

    df = pd.DataFrame(raw_data)
    if "symbol" in df.columns:
        df = df.dropna(subset=["symbol"])

    candidates = df.to_dict(orient="records")
    
    # Stamp strategy metadata onto each record bag
    for candidate in candidates:
        candidate["strategy_name"] = "extra_watchlist"
        candidate["timestamp"] = pd.Timestamp.utcnow().isoformat()

    logger.info(f"Retrieved {len(candidates)} raw candidates. Starting fundamental validation...")

    # --- Step 2: Fundamental Enrichment & Validation ---
    fund_validator = FundamentalValidator(client=client)
    fundamentally_sound = []
    
    for candidate in candidates:
        result = fund_validator.evaluate(candidate)
        if result:
            fundamentally_sound.append(result)

    logger.info(f"{len(fundamentally_sound)} symbols passed fundamental checks. Starting technical validation...")

    # --- Step 3: Technical Enrichment & Validation ---
    tech_validator = TechnicalValidator(client=client)
    final_watchlist = []
    
    for candidate in fundamentally_sound:
        result = tech_validator.evaluate(candidate)
        if result:
            final_watchlist.append(result)

    logger.info(f"✨ Extra Watchlist pipeline complete. {len(final_watchlist)} fully enriched records ready for BigQuery.")
    return final_watchlist


def run_market_down_pipeline() -> list:
    """
    Orchestrates the Market Down pipeline:
    1. Descriptive (NASDAQ, Mid-cap > $2B, High Short Float > 20%)
    2. Fundamental (Negative EPS growth next year)
    3. Technical (Price < SMA20 bearish alignment)
    """
    client = FMPClient()
    market_down_params = {
        "exchange": "NASDAQ",
        "marketCapMoreThan": 2000000000,  # Mid cap over $2B
        "country": "US",
        "isActivelyTrading": "true",
        "limit": 1000
    }
    
    logger.info("Running Market Down Step 1: Fetching descriptive universe...")
    raw_data = client.get_company_screener(market_down_params)

    if not raw_data:
        logger.warning("No data returned for Market Down descriptive screener.")
        return []

    df = pd.DataFrame(raw_data)
    
    if "shortFloat" in df.columns:
        df = df[df["shortFloat"] > 0.20]
        
    if "symbol" not in df.columns:
        return []
        
    symbols = df["symbol"].tolist()
    logger.info(f"Market Down descriptive universe secured: {len(symbols)} tickers.")

    # 2. Fundamentals (Negative EPS)
    logger.info("Running Market Down Step 2: Fundamental validation (Negative EPS)...")
    fund_validator = MarketDownFundamentalValidator(client)
    filtered_funds = [sym for sym in symbols if fund_validator.evaluate({"symbol": sym})]
    logger.info(f"{len(filtered_funds)} tickers passed fundamental checks.")

    # 3. Technicals (Price < SMA20)
    logger.info("Running Market Down Step 3: Technical validation (Price < SMA20)...")
    tech_validator = BearishTechnicalValidator(client)
    final_results = [sym for sym in filtered_funds if tech_validator.evaluate({"symbol": sym})]

    logger.info(f"Market Down pipeline complete. Final watchlist: {final_results}")
    return final_results


def run_high_growth_float_watchlist() -> list:
    """
    Orchestrates the High-Growth / Low-Float Watchlist Pipeline:
    1. Descriptive + Float Filter
    2. Fundamental Validation
    """
    client = FMPClient()
    
    logger.info("Running Step 1: Descriptive screener & float filtering...")
    base_params = {
        "priceMoreThan": 5,
        "avgVolumeMoreThan": 200000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": 1000
    }
    
    raw_data = client.get_company_screener(base_params)
    if not raw_data:
        return []

    df = pd.DataFrame(raw_data)
    
    if "floatShares" in df.columns:
        df = df[df["floatShares"] < 50000000]
        
    symbols = df["symbol"].tolist() if "symbol" in df.columns else []
    logger.info(f"Filtered down to {len(symbols)} candidate tickers after descriptive & float checks.")

    logger.info("Running Step 2: Fundamental validation...")
    validator = FundamentalValidator(
        client=client,
        min_eps_growth=0.20,
        min_roe=0.15,
        min_gross_margin=0.0,
        max_institutional_ownership=0.80
    )

    final_watchlist = [sym for sym in symbols if validator.evaluate({"symbol": sym})]
    logger.info(f"Pipeline complete. Final watchlist contains {len(final_watchlist)} stocks: {final_watchlist}")
    return final_watchlist


def run_swing_trading_pipeline() -> list:
    """
    Orchestrates the EOD Swing Trading Pipeline:
    1. Descriptive: Price > $10, Avg Vol > 200K, Relative Vol > 1.5
    2. Quote Filter: Price >= 5% below 52-week high (price <= yearHigh * 0.95)
    3. Fundamentals: Positive growth, ROE > 0, Inst. Ownership < 60%
    4. Technicals: Price > SMA20 > SMA50 > SMA200
    """
    client = FMPClient()
    
    logger.info("Running Swing Trading Step 1: Descriptive filters...")
    base_params = {
        "priceMoreThan": 10,
        "avgVolumeMoreThan": 200000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": 1000
    }
    
    raw_data = client.get_company_screener(base_params)
    if not raw_data:
        logger.warning("No data returned for Swing Trading screener.")
        return []

    df = pd.DataFrame(raw_data)
    
    if "relativeVolume" in df.columns:
        df = df[df["relativeVolume"] > 1.5]

    symbols = df["symbol"].tolist() if "symbol" in df.columns else []
    logger.info(f"Screened {len(symbols)} candidates. Checking 52-week high via quote endpoint...")

    # --- Step 1b: Quote Filtering (>= 5% below 52-week high) ---
    quote_filtered_symbols = []
    for symbol in symbols:
        quote_data = client.get_quote(symbol)
        if not quote_data:
            continue
        q = quote_data[0]
        price = q.get("price", 0)
        year_high = q.get("yearHigh", 0)
        
        if year_high and price <= year_high * 0.95:
            quote_filtered_symbols.append(symbol)

    logger.info(f"Filtered down to {len(quote_filtered_symbols)} candidates after 52-week high check.")

    # --- Step 2: Fundamental Validation ---
    logger.info("Running Swing Trading Step 2: Fundamental validation...")
    fund_validator = FundamentalValidator(
        client=client,
        min_eps_growth=0.0,
        min_roe=0.0,
        min_gross_margin=0.0,
        max_institutional_ownership=0.60
    )

    fundamentally_sound = [sym for sym in quote_filtered_symbols if fund_validator.evaluate({"symbol": sym})]
    logger.info(f"{len(fundamentally_sound)} symbols passed fundamental checks.")

    # --- Step 3: Technical Validation ---
    logger.info("Running Swing Trading Step 3: Technical validation...")
    tech_validator = TechnicalValidator(client)
    final_watchlist = [sym for sym in fundamentally_sound if tech_validator.evaluate({"symbol": sym})]

    logger.info(f"Swing Trading pipeline complete. Final watchlist: {final_watchlist}")
    return final_watchlist


def run_new_highs_pipeline() -> list:
    """
    Orchestrates the New Highs Momentum Pipeline:
    1. Descriptive: Price > $10, Avg Vol > 200K, Relative Vol > 1.0
    2. Quote Filter: Intraday Up & 52-Week New High (Price >= 99% of yearHigh)
    3. Fundamentals: Positive growth & Inst Ownership < 60%
    4. Technicals: Price above SMA20, SMA50, SMA200
    """
    client = FMPClient()
    
    logger.info("Running New Highs Step 1: Descriptive filters...")
    base_params = {
        "marketCapMoreThan": 300000000,
        "priceMoreThan": 10,
        "avgVolumeMoreThan": 200000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": 1000
    }
    
    raw_data = client.get_company_screener(base_params)
    if not raw_data:
        logger.warning("No data returned for New Highs screener.")
        return []

    df = pd.DataFrame(raw_data)
    
    if "relativeVolume" in df.columns:
        df = df[df["relativeVolume"] > 1.0]

    symbols = df["symbol"].tolist() if "symbol" in df.columns else []
    logger.info(f"Screened {len(symbols)} candidates. Evaluating live quotes & 52-week highs...")

    # --- Step 1b: Quote & New High Filtering ---
    new_high_candidates = []
    for symbol in symbols:
        quote_data = client.get_quote(symbol)
        if not quote_data:
            continue
        q = quote_data[0]
        price = q.get("price", 0)
        open_price = q.get("open", 0)
        prev_close = q.get("previousClose", 0)
        year_high = q.get("yearHigh", 0)
        
        # Check Intraday Up & 52-Week New High conditions
        if year_high and price and open_price and prev_close:
            if price > prev_close and price > open_price and price >= year_high * 0.99:
                new_high_candidates.append(symbol)

    logger.info(f"Filtered down to {len(new_high_candidates)} candidates meeting New High criteria.")

    # --- Step 2: Fundamental Validation ---
    logger.info("Running New Highs Step 2: Fundamental validation...")
    fund_validator = FundamentalValidator(
        client=client,
        min_eps_growth=0.0,
        min_roe=0.0,
        min_gross_margin=0.0,
        max_institutional_ownership=0.60
    )

    fundamentally_sound = [sym for sym in new_high_candidates if fund_validator.evaluate({"symbol": sym})]
    logger.info(f"{len(fundamentally_sound)} symbols passed fundamental checks.")

    # --- Step 3: Technical Validation ---
    logger.info("Running New Highs Step 3: Technical validation...")
    tech_validator = TechnicalValidator(client)
    final_watchlist = [sym for sym in fundamentally_sound if tech_validator.evaluate({"symbol": sym})]

    logger.info(f"New Highs pipeline complete. Final watchlist: {final_watchlist}")
    return final_watchlist