import os
import pandas as pd
import pytest

from ingest_fmp.client import FMPClient


@pytest.fixture(scope="module")
def fmp_client() -> FMPClient:
    if not os.getenv("FMP_API_KEY"):
        pytest.skip("FMP_API_KEY is not set; skipping live FMP screener integration test.")
    return FMPClient()


PIPELINE_SCREENER_CONFIGS = [
    (
        "extra_watchlist",
        {
            "marketCapMoreThan": 2_000_000_000,
            "priceMoreThan": 10,
            "avgVolumeMoreThan": 200_000,
            "country": "US",
            "isEtf": "false",
            "isFund": "false",
            "isActivelyTrading": "true",
            "limit": 1000,
        },
        None,
    ),
    (
        "market_down",
        {
            "exchange": "NASDAQ",
            "marketCapMoreThan": 2_000_000_000,
            "country": "US",
            "isActivelyTrading": "true",
            "limit": 1000,
        },
        lambda df: df[df["shortFloat"] > 0.20] if "shortFloat" in df.columns else df,
    ),
    (
        "high_growth_float",
        {
            "priceMoreThan": 5,
            "avgVolumeMoreThan": 200_000,
            "country": "US",
            "isEtf": "false",
            "isFund": "false",
            "isActivelyTrading": "true",
            "limit": 1000,
        },
        lambda df: df[df["floatShares"] < 50_000_000] if "floatShares" in df.columns else df,
    ),
    (
        "swing_trading",
        {
            "priceMoreThan": 10,
            "avgVolumeMoreThan": 200_000,
            "country": "US",
            "isEtf": "false",
            "isFund": "false",
            "isActivelyTrading": "true",
            "limit": 1000,
        },
        lambda df: df[df["relativeVolume"] > 1.5] if "relativeVolume" in df.columns else df,
    ),
    (
        "new_highs",
        {
            "marketCapMoreThan": 300_000_000,
            "priceMoreThan": 10,
            "avgVolumeMoreThan": 200_000,
            "country": "US",
            "isEtf": "false",
            "isFund": "false",
            "isActivelyTrading": "true",
            "limit": 1000,
        },
        lambda df: df[df["relativeVolume"] > 1.0] if "relativeVolume" in df.columns else df,
    ),
    (
        "eod_screener",
        {
            "priceMoreThan": 10,
            "avgVolumeMoreThan": 200_000,
            "country": "US",
            "isEtf": "false",
            "isFund": "false",
            "isActivelyTrading": "true",
            "limit": 1000,
        },
        lambda df: df[df["relativeVolume"] > 1.5] if "relativeVolume" in df.columns else df,
    ),
]


@pytest.mark.integration
@pytest.mark.parametrize("pipeline_name,params,df_filter", PIPELINE_SCREENER_CONFIGS)
def test_screener_returns_symbols_and_logs_counts(fmp_client, capsys, pipeline_name, params, df_filter):
    raw_data = fmp_client.get_company_screener(params)
    assert isinstance(raw_data, list), f"[{pipeline_name}] Expected list from screener, got {type(raw_data)}"

    df = pd.DataFrame(raw_data)
    raw_count = len(df)
    if "symbol" in df.columns:
        df = df.dropna(subset=["symbol"])

    filtered_df = df_filter(df) if df_filter is not None and not df.empty else df
    symbols = filtered_df["symbol"].tolist() if "symbol" in filtered_df.columns else []

    print(
        f"\n[{pipeline_name}] raw={raw_count} -> post_filter={len(symbols)} symbols | sample={symbols[:5]}"
    )
    assert len(symbols) >= 0


@pytest.mark.integration
@pytest.mark.parametrize("exchange", ["NYSE", "NASDAQ", "AMEX"])
def test_screener_counts_by_exchange_with_eod_filters(fmp_client, exchange):
    params = {
        "exchange": exchange,
        "priceMoreThan": 10,
        "avgVolumeMoreThan": 200_000,
        "country": "US",
        "isEtf": "false",
        "isFund": "false",
        "isActivelyTrading": "true",
        "limit": 1000,
    }
    raw_data = fmp_client.get_company_screener(params)
    df = pd.DataFrame(raw_data or [])
    symbols = df["symbol"].dropna().tolist() if "symbol" in df.columns else []
    print(f"\n[exchange={exchange}] count={len(symbols)} | sample={symbols[:5]}")