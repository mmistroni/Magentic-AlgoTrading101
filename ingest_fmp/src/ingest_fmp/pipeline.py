from ingest_fmp.client import FMPClient
from ingest_fmp.screeners import StockScreeners
from ingest_fmp.fundamental_validator import FundamentalValidator, MarketDownFundamentalValidator
from ingest_fmp.technical_validator import TechnicalValidator, BearishTechnicalValidator
import logging
from ingest_fmp.client import FMPClient
from ingest_fmp.screeners import StockScreeners
from ingest_fmp.fundamental_validator import FundamentalValidator
import logging
from ingest_fmp.client import FMPClient
from ingest_fmp.screeners import StockScreeners
from ingest_fmp.fundamental_validator import MarketDownFundamentalValidator
from ingest_fmp.technical_validator import BearishTechnicalValidator
import pandas as pd

logger = logging.getLogger(__name__)

def get_extra_watchlist():
    client = FMPClient()
    
    # Step 1: Descriptive Universe
    screeners = StockScreeners(client)
    base_stocks = screeners.get_base_universe()
    symbols = [stock["symbol"] for stock in base_stocks]

    # Step 2: Fundamental Enrichment
    fund_validator = FundamentalValidator(client)
    fundamentally_sound = [sym for sym in symbols if fund_validator.evaluate(sym)]

    # Step 3: Technical Enrichment (Run only on fundamentally qualified stocks)
    tech_validator = TechnicalValidator(client)
    final_watchlist = [sym for sym in fundamentally_sound if tech_validator.evaluate(sym)]

    return final_watchlist


def run_market_down_pipeline() -> list:
    """
    Orchestrates the Market Down pipeline:
    1. Descriptive (NASDAQ, Mid-cap > $2B, High Short Float > 20%)
    2. Fundamental (Negative EPS growth next year)
    3. Technical (Price < SMA20 bearish alignment)
    """
    client = FMPClient()
    screeners = StockScreeners(client)
    
    # 1. Define native FMP descriptive parameters
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
    
    # Optional local filter for Float Short > 20% (0.20) if the field is present in FMP payload
    if "shortFloat" in df.columns:
        df = df[df["shortFloat"] > 0.20]
        
    if "symbol" not in df.columns:
        return []
        
    symbols = df["symbol"].tolist()
    logger.info(f"Market Down descriptive universe secured: {len(symbols)} tickers.")

    # 2. Fundamentals (Negative EPS Next Year)
    logger.info("Running Market Down Step 2: Fundamental validation (Negative EPS)...")
    fund_validator = MarketDownFundamentalValidator(client)
    filtered_funds = [sym for sym in symbols if fund_validator.evaluate(sym)]
    logger.info(f"{len(filtered_funds)} tickers passed fundamental checks.")

    # 3. Technicals (Price < SMA20 & Downward momentum)
    logger.info("Running Market Down Step 3: Technical validation (Price < SMA20)...")
    tech_validator = BearishTechnicalValidator(client)
    final_results = [sym for sym in filtered_funds if tech_validator.evaluate(sym)]

    logger.info(f"Market Down pipeline complete. Final watchlist: {final_results}")
    return final_results



def run_high_growth_float_watchlist() -> list:
    """
    Orchestrates the High-Growth / Low-Float Watchlist Pipeline:
    1. Descriptive + Float Filter
    2. Fundamental Validation (>20% EPS, >25% Sales/Next-Year, >15% ROE, >20% Inst Ownership)
    """
    client = FMPClient()
    
    # --- Step 1: Descriptive & Float Filtering ---
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
    
    screeners = StockScreeners(client)
    raw_data = client.get_company_screener(base_params)
    if not raw_data:
        return []

    df = pd.DataFrame(raw_data)
    
    # Filter Float < 50M locally via Pandas
    if "floatShares" in df.columns:
        df = df[df["floatShares"] < 50000000]
        
    symbols = df["symbol"].tolist() if "symbol" in df.columns else []
    logger.info(f"Filtered down to {len(symbols)} candidate tickers after descriptive & float checks.")

    # --- Step 2: Parameterized Fundamental Validation ---
    logger.info("Running Step 2: Fundamental validation...")
    validator = FundamentalValidator(
        client=client,
        min_eps_this_year=0.20,          # Over 20%
        min_eps_next_year=0.25,          # Over 25%
        min_eps_qtr=0.20,                # Over 20%
        min_sales_qtr=0.25,              # Over 25%
        min_roe=0.15,                    # Over 15%
        min_gross_margin=0.0,            # Positive (>0%)
        min_institutional_ownership=0.20 # Over 20%
    )

    final_watchlist = [sym for sym in symbols if validator.evaluate(sym)]
    
    logger.info(f"Pipeline complete. Final watchlist contains {len(final_watchlist)} stocks: {final_watchlist}")
    return final_watchlist


def run_swing_trading_pipeline() -> list:
    """
    Orchestrates the EOD Swing Trading Pipeline:
    1. Descriptive: Price > $10, Avg Vol > 200K, Relative Vol > 1.5
    2. Fundamentals: Positive growth across EPS/Sales, ROE > 0, 
       Inst. Ownership < 60%, Debt/Equity < 1, Current Ratio > 1
    3. Technicals: Price > SMA20 > SMA50 > SMA200 AND >= 5% below 52-week high
    """
    client = FMPClient()
    screeners = StockScreeners(client)
    
    # --- Step 1: Descriptive & Relative Volume Filtering ---
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
    
    # Filter Relative Volume > 1.5 locally if column exists
    if "relativeVolume" in df.columns:
        df = df[df["relativeVolume"] > 1.5]

    # Filter 5% or more below 52-week high if columns exist
    if "price" in df.columns and "yearHigh" in df.columns:
        df = df[df["price"] <= df["yearHigh"] * 0.95]

    symbols = df["symbol"].tolist() if "symbol" in df.columns else []
    logger.info(f"Filtered down to {len(symbols)} candidates after descriptive and relative volume checks.")

    # --- Step 2: Fundamental Validation (Swing Profile) ---
    logger.info("Running Swing Trading Step 2: Fundamental validation...")
    fund_validator = FundamentalValidator(
        client=client,
        min_eps_this_year=0.0,           # Positive (>0%)
        min_eps_next_year=0.0,           # Positive (>0%)
        min_eps_qtr=0.0,                 # Positive (>0%)
        min_sales_qtr=0.0,               # Positive (>0%)
        min_roe=0.0,                     # Positive (>0%)
        max_institutional_ownership=0.60,# Under 60%
        max_debt_to_equity=1.0,          # Under 1
        min_current_ratio=1.0            # Over 1
    )

    fundamentally_sound = [sym for sym in symbols if fund_validator.evaluate(sym)]
    logger.info(f"{len(fundamentally_sound)} symbols passed fundamental checks.")

    # --- Step 3: Technical Validation (Bullish SMAs) ---
    logger.info("Running Swing Trading Step 3: Technical validation (SMA alignment)...")
    tech_validator = TechnicalValidator(client)
    final_watchlist = [sym for sym in fundamentally_sound if tech_validator.evaluate(sym)]

    logger.info(f"Swing Trading pipeline complete. Final watchlist: {final_watchlist}")
    return final_watchlist