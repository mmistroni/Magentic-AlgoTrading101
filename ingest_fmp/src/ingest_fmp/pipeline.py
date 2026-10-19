from ingest_fmp.client import FMPClient
from ingest_fmp.screeners import StockScreeners
from ingest_fmp.fundamental_validator import FundamentalValidator, MarketDownFundamentalValidator
from ingest_fmp.technical_validator import TechnicalValidator, BearishTechnicalValidator

def run_enrichment_pipeline():
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

def run_market_down_pipeline():
    client = FMPClient()
    
    # 1. Descriptive
    screeners = StockScreeners(client)
    base_stocks = screeners.get_custom_universe(market_down_params)
    symbols = [s["symbol"] for s in base_stocks]

    # 2. Fundamentals (Negative EPS Next Year)
    fund_validator = MarketDownFundamentalValidator(client)
    filtered_funds = [sym for sym in symbols if fund_validator.evaluate(sym)]

    # 3. Technicals (Price < SMA20 & Downward momentum)
    tech_validator = BearishTechnicalValidator(client)
    final_results = [sym for sym in filtered_funds if tech_validator.evaluate(sym)]

    return final_results