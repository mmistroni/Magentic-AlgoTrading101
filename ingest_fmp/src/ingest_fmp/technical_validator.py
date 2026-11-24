import logging
import math
from datetime import datetime, timedelta, timezone
import numpy as np
import pandas as pd
import requests
from ta.momentum import AwesomeOscillatorIndicator, RSIIndicator
from ta.trend import ADXIndicator
from ta.volume import ChaikinMoneyFlowIndicator, OnBalanceVolumeIndicator

from ingest_fmp.client import FMPClient

logger = logging.getLogger(__name__)

DEFAULT_LOOKBACK_DAYS = 450


def _to_py_float(val) -> float | None:
    """Safely converts numeric/numpy values to plain Python float or None."""
    if val is None:
        return None
    try:
        if pd.isna(val):
            return None
        f = float(val)
        return None if math.isnan(f) or math.isinf(f) else f
    except (TypeError, ValueError):
        return None


def _to_py_float_list(values) -> list[float]:
    """Converts an iterable of values into a list of clean Python floats."""
    cleaned: list[float] = []
    if not values:
        return cleaned
    for v in values:
        fv = _to_py_float(v)
        if fv is not None:
            cleaned.append(fv)
    return cleaned


class BaseTechnicalValidator:
    """Base class computing SMAs and TA indicators locally from historical OHLCV data."""

    def __init__(
        self,
        client: FMPClient,
        throttle_seconds: float = 0.0,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ):
        self.client = client
        self.throttle_seconds = throttle_seconds
        self.lookback_days = lookback_days
        self._cached_spy_df: pd.DataFrame | None = None

    def _get_symbol(self, symbol_dict: dict) -> str:
        """Helper to safely retrieve the ticker/symbol from the dictionary."""
        return symbol_dict.get("symbol") or symbol_dict.get("ticker", "")

    def _fetch_historical_df(self, symbol: str, lookback_days: int | None = None) -> pd.DataFrame:
        """Fetches historical daily OHLCV data for the last N calendar days as a clean DataFrame."""
        days = lookback_days if lookback_days is not None else self.lookback_days
        end_date = datetime.now(timezone.utc).date()
        start_date = end_date - timedelta(days=days)

        raw_rows: list[dict] = []
        try:
            api_key = getattr(self.client, "api_key", None)
            if not api_key:
                return pd.DataFrame()

            hist_url = (
                f"https://financialmodelingprep.com/api/v3/historical-price-full/{symbol}"
                f"?from={start_date.isoformat()}&to={end_date.isoformat()}&apikey={api_key}"
            )
            resp = requests.get(hist_url, timeout=15)
            if self.throttle_seconds > 0:
                import time
                time.sleep(self.throttle_seconds)

            if resp.status_code == 200:
                payload = resp.json()
                if isinstance(payload, dict):
                    raw_rows = payload.get("historical", []) or []
                elif isinstance(payload, list):
                    raw_rows = payload
        except Exception as e:
            logger.error(f"Error fetching historical data for {symbol}: {str(e)}")
            return pd.DataFrame()

        if not raw_rows:
            return pd.DataFrame()

        df = pd.DataFrame(raw_rows)
        if df.empty or "close" not in df.columns:
            return pd.DataFrame()

        if "date" in df.columns:
            df["date"] = pd.to_datetime(df["date"], errors="coerce")
            df = df.dropna(subset=["date"]).sort_values("date").drop_duplicates(subset=["date"])
        else:
            df = df.iloc[::-1]

        df = df.reset_index(drop=True)

        for col in ("open", "high", "low", "close", "volume"):
            if col in df.columns:
                df[col] = pd.to_numeric(df[col], errors="coerce")

        return df

    def _get_spy_benchmark(self) -> pd.DataFrame:
        """Fetches and caches SPY benchmark history once per validator session."""
        if self._cached_spy_df is not None:
            return self._cached_spy_df

        spy_df = self._fetch_historical_df("SPY", lookback_days=self.lookback_days)
        self._cached_spy_df = spy_df if spy_df is not None else pd.DataFrame()
        return self._cached_spy_df

    def _compute_local_smas(self, df: pd.DataFrame) -> dict:
        """Computes latest close and SMA20, SMA50, SMA200 locally from historical close series."""
        if df is None or df.empty or "close" not in df.columns:
            return {"price": None, "SMA20": None, "SMA50": None, "SMA200": None}

        closes = df["close"]
        price = _to_py_float(closes.iloc[-1]) if len(closes) >= 1 else None
        sma20 = _to_py_float(closes.rolling(window=20).mean().iloc[-1]) if len(closes) >= 20 else None
        sma50 = _to_py_float(closes.rolling(window=50).mean().iloc[-1]) if len(closes) >= 50 else None
        sma200 = _to_py_float(closes.rolling(window=200).mean().iloc[-1]) if len(closes) >= 200 else None

        return {
            "price": price,
            "SMA20": sma20,
            "SMA50": sma50,
            "SMA200": sma200,
        }

    def _calculate_choppiness(self, df: pd.DataFrame, window: int = 14) -> float | None:
        """Calculates Choppiness Index."""
        try:
            if len(df) < window or not {"high", "low", "close"}.issubset(df.columns):
                return None
            high_low = df["high"] - df["low"]
            high_close = np.abs(df["high"] - df["close"].shift(1))
            low_close = np.abs(df["low"] - df["close"].shift(1))
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            tr_sum = tr.rolling(window=window).sum()
            max_h = df["high"].rolling(window=window).max()
            min_l = df["low"].rolling(window=window).min()
            denom = max_h - min_l
            chop = 100 * (np.log10(tr_sum / denom.replace(0, np.nan)) / np.log10(window))
            return _to_py_float(chop.iloc[-1])
        except Exception:
            return None

    def _calculate_spx_choppiness(self) -> float | None:
        """Calculates benchmark SPY Choppiness Index."""
        try:
            spy_df = self._get_spy_benchmark()
            if spy_df.empty:
                return None
            return self._calculate_choppiness(spy_df)
        except Exception:
            return None

    def _calculate_beta(self, df: pd.DataFrame) -> float | None:
        """Calculates stock beta relative to benchmark SPY (aligning by date when available)."""
        try:
            spy_df = self._get_spy_benchmark()
            if spy_df.empty or "close" not in spy_df.columns or "close" not in df.columns:
                return None

            if "date" in df.columns and "date" in spy_df.columns:
                stock_s = df.set_index("date")["close"].pct_change()
                spy_s = spy_df.set_index("date")["close"].pct_change()
                aligned = pd.concat([stock_s, spy_s], axis=1, join="inner").dropna()
            else:
                stock_ret = df["close"].pct_change()
                market_ret = spy_df["close"].pct_change()
                aligned = pd.concat([stock_ret, market_ret], axis=1).dropna()

            if len(aligned) < 30:
                return None

            cov = aligned.iloc[:, 0].cov(aligned.iloc[:, 1])
            var = aligned.iloc[:, 1].var()
            if var is None or var == 0 or pd.isna(cov) or pd.isna(var):
                return None
            return _to_py_float(cov / var)
        except Exception:
            return None

    def _calculate_slope(self, closes: pd.Series, window: int = 20) -> float | None:
        """Calculates linear regression slope over the last N periods."""
        try:
            clean_closes = closes.dropna()
            if len(clean_closes) < window:
                return None
            y = clean_closes.iloc[-window:].to_numpy(dtype=float)
            x = np.arange(window, dtype=float)
            slope, _ = np.polyfit(x, y, 1)
            return _to_py_float(slope)
        except Exception:
            return None

    def _calculate_trend_velocity_gap(self, df: pd.DataFrame) -> float | None:
        """Calculates normalized difference between SMA20 and SMA50."""
        try:
            if len(df) < 50 or "close" not in df.columns:
                return None
            sma20 = df["close"].rolling(20).mean().iloc[-1]
            sma50 = df["close"].rolling(50).mean().iloc[-1]
            if sma50 is None or sma50 == 0 or pd.isna(sma20) or pd.isna(sma50):
                return None
            return _to_py_float((sma20 - sma50) / sma50)
        except Exception:
            return None

    def _calculate_fib_161(self, df: pd.DataFrame, window: int = 50) -> float | None:
        """Calculates Fibonacci 1.618 extension target based on recent swing high/low."""
        try:
            if len(df) < window or not {"high", "low"}.issubset(df.columns):
                return None
            recent = df.iloc[-window:]
            swing_high = recent["high"].max()
            swing_low = recent["low"].min()
            if pd.isna(swing_high) or pd.isna(swing_low):
                return None
            return _to_py_float(swing_low + 1.618 * (swing_high - swing_low))
        except Exception:
            return None

    def _compute_ta_indicators_from_df(self, symbol: str, df: pd.DataFrame) -> dict:
        """Computes OBV, CMF, Choppiness, DeMarker, EWO, RSI, ADX, and advanced metrics from OHLCV df."""
        try:
            if df is None or df.empty or not {"close", "volume", "high", "low"}.issubset(df.columns):
                return {}

            work_df = df.copy()

            # 1. OBV & CMF
            work_df["obv"] = OnBalanceVolumeIndicator(
                close=work_df["close"], volume=work_df["volume"]
            ).on_balance_volume()
            work_df["cmf"] = ChaikinMoneyFlowIndicator(
                high=work_df["high"],
                low=work_df["low"],
                close=work_df["close"],
                volume=work_df["volume"],
            ).chaikin_money_flow()

            # 2. RSI & ADX
            work_df["rsi"] = RSIIndicator(close=work_df["close"], window=14).rsi()
            work_df["adx"] = ADXIndicator(
                high=work_df["high"], low=work_df["low"], close=work_df["close"], window=14
            ).adx()

            # 3. Choppiness & DeMarker
            window = 14
            high_low = work_df["high"] - work_df["low"]
            high_close = np.abs(work_df["high"] - work_df["close"].shift(1))
            low_close = np.abs(work_df["low"] - work_df["close"].shift(1))
            tr = pd.concat([high_low, high_close, low_close], axis=1).max(axis=1)
            tr_sum = tr.rolling(window=window).sum()
            max_h = work_df["high"].rolling(window=window).max()
            min_l = work_df["low"].rolling(window=window).min()
            denom = max_h - min_l
            work_df["choppiness"] = 100 * (
                np.log10(tr_sum / denom.replace(0, np.nan)) / np.log10(window)
            )

            high_diff = work_df["high"] - work_df["high"].shift(1)
            demax = high_diff.where(high_diff > 0, 0.0)
            low_diff = work_df["low"].shift(1) - work_df["low"]
            demin = low_diff.where(low_diff > 0, 0.0)
            dem_denom = demax.rolling(window=window).mean() + demin.rolling(window=window).mean()
            work_df["demarker"] = demax.rolling(window=window).mean() / dem_denom.replace(0, np.nan)

            last = work_df.iloc[-1]
            prev = work_df.iloc[-2] if len(work_df) > 1 else last

            # 4. Advanced indicator calculations
            spx_choppy_val = self._calculate_spx_choppiness()
            beta_val = self._calculate_beta(work_df)
            slope_val = self._calculate_slope(work_df["close"])
            trend_velocity_gap_val = self._calculate_trend_velocity_gap(work_df)
            fib_161_val = self._calculate_fib_161(work_df)
            ewo_series = AwesomeOscillatorIndicator(
                high=work_df["high"], low=work_df["low"]
            ).awesome_oscillator()

            return {
                "previous_obv": _to_py_float(prev.get("obv")),
                "current_obv": _to_py_float(last.get("obv")),
                "obv_last_20_days": _to_py_float_list(work_df["obv"].dropna().tolist()[-20:]),
                "previous_cmf": _to_py_float(prev.get("cmf")),
                "last_cmf": _to_py_float(last.get("cmf")),
                "cmf_last_20_days": _to_py_float_list(work_df["cmf"].dropna().tolist()[-20:]),
                "choppiness": _to_py_float(last.get("choppiness")),
                "demarker": _to_py_float(last.get("demarker")),
                "ewo": _to_py_float(ewo_series.iloc[-1] if len(ewo_series) > 0 else None),
                "RSI": _to_py_float(last.get("rsi")),
                "ADX": _to_py_float(last.get("adx")),
                "beta": beta_val,
                "spx_choppyness": spx_choppy_val,
                "slope": slope_val,
                "trend_velocity_gap": trend_velocity_gap_val,
                "fib_161": fib_161_val,
            }
        except Exception as e:
            logger.error(f"Error computing TA indicators for {symbol}: {str(e)}")
            return {}


class TechnicalValidator(BaseTechnicalValidator):
    def __init__(
        self,
        client: FMPClient,
        throttle_seconds: float = 0.0,
        strict_mode: bool = True,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ):
        super().__init__(client, throttle_seconds=throttle_seconds, lookback_days=lookback_days)
        self.strict_mode = strict_mode

    def evaluate(self, symbol_dict: dict) -> dict:
        symbol = self._get_symbol(symbol_dict)
        try:
            df = self._fetch_historical_df(symbol)
            sma_data = self._compute_local_smas(df)

            price = sma_data["price"]
            sma20 = sma_data["SMA20"]
            sma50 = sma_data["SMA50"]
            sma200 = sma_data["SMA200"]

            passed_bullish = bool(
                price is not None
                and sma20 is not None
                and sma50 is not None
                and sma200 is not None
                and (price > sma20 > sma50 > sma200)
            )

            if self.strict_mode and not passed_bullish:
                return {}

            ta_metrics = self._compute_ta_indicators_from_df(symbol, df)

            symbol_dict.update(
                {
                    "price": price,
                    "SMA20": sma20,
                    "SMA50": sma50,
                    "SMA200": sma200,
                    "technical_passed": passed_bullish,
                    **ta_metrics,
                }
            )
            return symbol_dict

        except Exception as e:
            logger.error(f"Error evaluating technicals for {symbol}: {str(e)}")
            return symbol_dict if not self.strict_mode else {}


class BearishTechnicalValidator(BaseTechnicalValidator):
    def __init__(
        self,
        client: FMPClient,
        throttle_seconds: float = 0.0,
        lookback_days: int = DEFAULT_LOOKBACK_DAYS,
    ):
        super().__init__(client, throttle_seconds=throttle_seconds, lookback_days=lookback_days)

    def evaluate(self, symbol_dict: dict) -> dict:
        """Validates bearish technicals: Price < SMA20 with supplementary SMA & TA data."""
        symbol = self._get_symbol(symbol_dict)
        try:
            df = self._fetch_historical_df(symbol)
            sma_data = self._compute_local_smas(df)

            price = sma_data["price"]
            sma20 = sma_data["SMA20"]
            sma50 = sma_data["SMA50"]
            sma200 = sma_data["SMA200"]

            if price is None or sma20 is None or price >= sma20:
                return {}
            if sma50 is None or sma200 is None:
                return {}

            ta_metrics = self._compute_ta_indicators_from_df(symbol, df)

            logger.info(f"📉 {symbol} passed bearish technical filters.")
            symbol_dict.update(
                {
                    "price": price,
                    "SMA20": sma20,
                    "SMA50": sma50,
                    "SMA200": sma200,
                    **ta_metrics,
                }
            )
            return symbol_dict

        except Exception as e:
            logger.error(f"Error evaluating bearish technicals for {symbol}: {str(e)}")
            return {}