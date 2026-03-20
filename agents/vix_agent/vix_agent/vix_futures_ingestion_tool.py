import os
import pandas as pd
import vix_utils  # Ensure this is installed

def _get_front_month_for_date(target_date: str) -> pd.DataFrame:
    """
    Extracts the continuous front-month (M1) VIX futures history 
    up to the specific target_date to avoid forward-looking bias.
    """
    # 1. Load the full term structure from vix_utils
    # This downloads/loads the historical futures data
    term_structure = vix_utils.load_vix_term_structure()
    
    # 2. Ensure the index is datetime for proper filtering
    term_structure.index = pd.to_datetime(term_structure.index)
    target_dt = pd.to_datetime(target_date)
    
    # 3. Filter data up to the target_date (Crucial for backtesting!)
    historical_data = term_structure.loc[:target_dt]
    
    # 4. Extract the Front Month (Tenor 1) Close/Settle price
    # vix_utils typically uses integer column names for tenors (1 = front month, 2 = second month)
    try:
        # Assuming a standard vix_utils MultiIndex structure: column 1, subcolumn 'Close' or 'Settle'
        if 'Close' in historical_data[1].columns:
            front_month_price = historical_data[1]['Close']
        else:
            front_month_price = historical_data[1]['Settle']
    except KeyError:
        # Fallback if the library version formats columns differently
        front_month_price = historical_data.iloc[:, 0] # Just grab the first data column
        
    # 5. Format into a clean DataFrame for merging
    df_out = pd.DataFrame({'vix_front_month_close': front_month_price})
    df_out.index.name = 'date'
    
    return df_out

def vix_futures_ingestion_tool(current_date: str) -> str:
    """
    TOOL: Fetches VIX Futures up to `current_date`, saves it to a RAW data file, 
    and returns the URI string.
    """
    print(f"Futures Ingestion Tool: Fetching VIX Futures up to {current_date}...")
    
    file_path = "./temp_data/vix_futures_raw_test.csv"
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    
    # Get the date-filtered data
    df_futures = _get_front_month_for_date(current_date)
    
    # Save RAW data for the pipeline to consume
    df_futures.to_csv(file_path, header=True)
    
    return file_path