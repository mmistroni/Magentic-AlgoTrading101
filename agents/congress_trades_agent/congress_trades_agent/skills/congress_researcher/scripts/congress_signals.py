# skills/CongressResearcher/scripts/fetch_congress_data.py

from pathlib import Path
import pandas as pd
from google.cloud import bigquery
from .market_regime import check_market_regime

# Locate the SQL file relative to this script
SKILL_DIR = Path(__file__).parent.parent
SQL_PATH = SKILL_DIR / "references" / "fetch_net_buy_signals.sql"

def get_bq_data(analysis_date: str) -> list:
    """Internal: Runs the Net Buy Activity SQL Algorithm with Parameterized Query."""
    bq_client = bigquery.Client()
    qry = SQL_PATH.read_text(encoding="utf-8")
    
    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ScalarQueryParameter("analysis_date", "STRING", analysis_date)
        ]
    )
    
    df = bq_client.query(qry, job_config=job_config).to_dataframe()
    
    if df.empty:
        return []

    # Pandas filtering logic
    df_filtered = df[
        (df['sale_count'] == 0) &
        ~df['ticker'].str.contains('DFCEX|VWLUX|LDNXF|TNA|AAL|BRK/B', case=False, na=False)
    ].copy()
    
    if df_filtered.empty:
        return []

    # Market regime enrichment
    df_filtered['market_uptrend'] = df_filtered['signal_date'].apply(
        lambda x: check_market_regime(x, analysis_date)
    )
    
    df_filtered['signal_date'] = df_filtered['signal_date'].astype(str)
    df_filtered['last_trade_date'] = df_filtered['last_trade_date'].astype(str)
    
    return df_filtered.to_dict(orient='records')