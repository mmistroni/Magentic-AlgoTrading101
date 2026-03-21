import os
import pandas as pd
import warnings
import vix_utils  

# Suppress the FutureWarnings coming from the 3rd party vix_utils package
warnings.filterwarnings("ignore", category=FutureWarning, module="vix_utils")

def _get_front_month_for_date(target_date: str) -> pd.DataFrame:
    """
    Extracts the continuous front-month (M1) VIX futures history 
    up to the specific target_date to avoid forward-looking bias.
    """
    term_structure = vix_utils.load_vix_term_structure()
    term_structure.index = pd.to_datetime(term_structure.index).tz_localize(None)
    target_dt = pd.to_datetime(target_date).tz_localize(None)
    
    term_structure = term_structure.sort_index()
    historical_data = term_structure[term_structure.index <= target_dt]
    
    try:
        if 'Close' in historical_data[1].columns:
            front_month_price = historical_data[1]['Close']
        else:
            front_month_price = historical_data[1]['Settle']
    except KeyError:
        front_month_price = historical_data.iloc[:, 0]
        
    df_out = pd.DataFrame({'vix_front_month_close': front_month_price})
    df_out.index.name = 'date'
    
    return df_out


# --- BIGQUERY EXTRACTOR ---
def fetch_vix_futures_from_bq(target_date: str) -> pd.DataFrame:
    """REAL function that will eventually query BigQuery for VIX Futures."""
    # TODO: Add real BigQuery logic later. 
    # For now, it falls back to the local vix_utils library if not mocked!
    return _get_front_month_for_date(target_date)


# --- INGESTION TOOL ---
def vix_futures_ingestion_tool(current_date: str) -> str:
    """
    TOOL: Fetches VIX Futures up to `current_date`, saves it to a RAW data file.
    """
    print(f"Futures Ingestion Tool: Fetching VIX Futures up to {current_date}...")
    
    file_path = "./temp_data/vix_futures_raw_test.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # 💥 Calls the BQ function!
    df_futures = fetch_vix_futures_from_bq(current_date)
    
    df_futures.to_csv(file_path, header=True, index=False)
    
    return file_path