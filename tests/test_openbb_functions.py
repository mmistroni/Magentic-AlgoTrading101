import pytest
from openbb_functions import get_ticker_from_query, get_company_overview, get_stock_price
from finvizfinance.screener.overview import Overview

import pandas as pd
# Example usage with a potential Wikipedia URL for GICS:

def get_gics_industries(wikipedia_url = "https://en.wikipedia.org/wiki/Global_Industry_Classification_Standard"):
    """
    Retrieves the GICS sectors and their corresponding industries from a Wikipedia page
    and returns them in a Pandas DataFrame.

    Args:
        wikipedia_url (str): The URL of the Wikipedia page containing the GICS structure.

    Returns:
        pandas.DataFrame: A DataFrame with columns 'Sector' and 'Industry'.
                          Returns an empty DataFrame if no suitable table is found.
    """
    try:
        # Read all tables from the HTML content of the Wikipedia page
        tables = pd.read_html(wikipedia_url)

        # Look for a table that contains the GICS sectors and industries
        gics_df = None
        for table in tables:
            # Check if the table has at least two columns and if the first column
            # seems to contain sector names (e.g., 'Energy', 'Materials')
            if len(table.columns) >= 2 and 'Sector' in table.columns and 'Industry' in table.columns:
                # Assuming the table has a structure where sectors and related
                # information are in adjacent columns. This might need adjustment
                # based on the exact Wikipedia page structure.

                # Try to find a column that looks like 'Sector' and another that
                # looks like 'Industry' or similar.
                sector_col = None
                industry_col = None

                for col in table.columns:
                    if 'Sector' in str(col):
                        sector_col = col
                    elif 'Industry' in str(col) or 'Sub-Industry' in str(col):
                        industry_col = col

                if sector_col is not None and industry_col is not None:
                    # Extract the Sector and Industry columns
                    gics_df = pd.DataFrame({
                        'Sector': table[sector_col].astype(str),
                        'Industry': table[industry_col].astype(str)
                    })
                    # Clean up rows that might contain headers or other non-data entries
                    gics_df = gics_df[gics_df['Sector'].str.contains(r'^\d{4}\s', regex=True, na=False) |
                                      gics_df['Sector'].str.contains(r'^(Energy|Materials|Industrials|Consumer Discretionary|Consumer Staples|Health Care|Financials|Information Technology|Communication Services|Utilities|Real Estate)$', regex=True, na=False)]
                    gics_df = gics_df[~gics_df['Industry'].str.contains('GICS Sector|GICS Industry Group|GICS Industry|GICS Sub-Industry', na=False)]
                    return gics_df
                elif sector_col is not None:
                    # If only a 'Sector' like column is found, we might need to make assumptions
                    # based on the structure of the table. This is a more general approach.
                    # Look for rows that seem to delineate sectors and their subsequent industries.
                    sector = None
                    industries = []
                    sector_industries = []
                    for index, row in table.iterrows():
                        if any(str(item).lower() in ['energy', 'materials', 'industrials', 'consumer discretionary',
                                                    'consumer staples', 'health care', 'financials',
                                                    'information technology', 'communication services', 'utilities',
                                                    'real estate'] for item in row.astype(str).values):
                            sector = row.iloc[0] # Assuming sector name is in the first column
                        elif sector is not None and len(row) > 0 and not any(str(item).lower() in ['gics'] for item in row.astype(str).values):
                            industry = ' '.join(row.astype(str).values).strip()
                            if industry:
                                sector_industries.append({'Sector': sector, 'Industry': industry})
                    if sector_industries:
                        return pd.DataFrame(sector_industries)

        return pd.DataFrame(columns=['Sector', 'Industry'])

    except Exception as e:
        print(f"An error occurred: {e}")
        return pd.DataFrame(columns=['Sector', 'Industry'])


def test_get_ticker_from_query():
    qry = 'What is the company profile  for COLM'
    assert 'COLM' == get_ticker_from_query(qry)

def test_get_stock_price():
    qry = 'What is the latest stock price for XOM'
    res = get_stock_price(qry)

    print(res)

    assert res


def test_get_company_overview():
    qry = 'What is the company profile  for COLM'
    res  =get_company_overview(qry)
    print (res)


    assert res is not None
    assert len(res) > 0

def get_companies_for_sect(sect):
    try:
        foverview = Overview()
        filters_dict = {'Sector': sect}
        foverview.set_filter(filters_dict=filters_dict)
        df = foverview.screener_view()
        return df.shape[0]
    except Exception as e:
        print(f"An error occurred while querying Finviz for sector '{sect}': {e}")
        return 0


def test_get_gics():
    ''' get industries '''
    df = get_gics_industries()

    # need to map to these https://www.msci.com/our-solutions/indexes/gics but wont work.
    if df.shape[0] > 1:

        sectors = df['Sector'].unique()
        for sector in sectors:
            if 'Materials' in sector:
                continue
            nc = get_companies_for_sect(sector)
            assert nc > 0, f'failed for {sector}'

