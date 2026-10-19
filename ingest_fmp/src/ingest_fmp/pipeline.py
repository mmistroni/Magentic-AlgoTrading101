from ingest_fmp.client import FMPClient
from ingest_fmp.screeners import StockScreeners
from ingest_fmp.fundamental_validator import FundamentalValidator
from ingest_fmp.technical_validator import TechnicalValidator

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