"""
Feature Engineering for ML models.
Computes 32 technical indicators from OHLCV data.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from typing import List, Dict


def _ema(s: pd.Series, p: int) -> pd.Series:
    return s.ewm(span=p, adjust=False).mean()


def _rsi(s: pd.Series, p: int = 14) -> pd.Series:
    d = s.diff()
    gain = d.clip(lower=0).ewm(com=p-1, adjust=False).mean()
    loss = (-d).clip(lower=0).ewm(com=p-1, adjust=False).mean()
    return 100 - (100 / (1 + gain / (loss + 1e-9)))


def build_features(ohlcv: List[Dict]) -> pd.DataFrame:
    if len(ohlcv) < 50:
        raise ValueError(f"Need ≥50 bars, got {len(ohlcv)}")

    df = pd.DataFrame(ohlcv)
    for col in ["open", "high", "low", "close", "volume"]:
        df[col] = pd.to_numeric(df[col], errors="coerce")
    df = df.dropna(subset=["close"]).reset_index(drop=True)

    close, high, low, vol = df["close"], df["high"], df["low"], df["volume"]

    # Price features
    df["returns"]      = close.pct_change()
    df["log_returns"]  = np.log(close / close.shift(1))
    df["hl_range"]     = (high - low) / (close + 1e-9)
    df["oc_range"]     = (close - df["open"]) / (df["open"] + 1e-9)

    # Moving averages
    df["ema_9"]  = _ema(close, 9)
    df["ema_20"] = _ema(close, 20)
    df["ema_50"] = _ema(close, 50)
    df["sma_20"] = close.rolling(20).mean()

    # MA ratios
    df["price_vs_ema20"] = (close - df["ema_20"]) / (df["ema_20"] + 1e-9)
    df["price_vs_ema50"] = (close - df["ema_50"]) / (df["ema_50"] + 1e-9)
    df["ema9_vs_ema20"]  = (df["ema_9"] - df["ema_20"]) / (df["ema_20"] + 1e-9)
    df["ema20_vs_ema50"] = (df["ema_20"] - df["ema_50"]) / (df["ema_50"] + 1e-9)
    df["ema9_slope"]     = df["ema_9"].diff(3) / (df["ema_9"].shift(3) + 1e-9)

    # RSI
    df["rsi_14"] = _rsi(close, 14)
    df["rsi_7"]  = _rsi(close, 7)
    df["rsi_14_norm"] = df["rsi_14"] / 100
    df["rsi_oversold"]  = (df["rsi_14"] < 30).astype(float)
    df["rsi_overbought"]= (df["rsi_14"] > 70).astype(float)

    # MACD
    ema12 = _ema(close, 12)
    ema26 = _ema(close, 26)
    df["macd_line"]      = ema12 - ema26
    df["macd_signal"]    = _ema(df["macd_line"], 9)
    df["macd_histogram"] = df["macd_line"] - df["macd_signal"]
    df["macd_line_norm"] = df["macd_line"] / (close + 1e-9)
    df["macd_hist_norm"] = df["macd_histogram"] / (close + 1e-9)
    df["macd_above_sig"] = (df["macd_line"] > df["macd_signal"]).astype(float)

    # Bollinger Bands
    bb_mid = close.rolling(20).mean()
    bb_std = close.rolling(20).std()
    bb_up  = bb_mid + 2 * bb_std
    bb_dn  = bb_mid - 2 * bb_std
    bb_w   = bb_up - bb_dn
    df["bb_position"] = (close - bb_dn) / (bb_w + 1e-9)
    df["bb_squeeze"]  = bb_w / (bb_mid + 1e-9)

    # ATR
    tr = pd.concat([high - low,
                    (high - close.shift()).abs(),
                    (low  - close.shift()).abs()], axis=1).max(axis=1)
    df["atr_14"]      = tr.rolling(14).mean()
    df["atr_14_norm"] = df["atr_14"] / (close + 1e-9)

    # Volume
    df["vol_sma20"]    = vol.rolling(20).mean()
    df["vol_ratio"]    = vol / (df["vol_sma20"] + 1e-9)
    df["vol_momentum"] = vol.rolling(5).mean() / (vol.rolling(20).mean() + 1e-9)

    # OBV
    df["obv"]      = (np.sign(close.diff()) * vol).cumsum()
    df["obv_ema"]  = _ema(df["obv"], 20)
    df["obv_trend"]= (df["obv"] - df["obv_ema"]) / (df["obv_ema"].abs() + 1e-9)

    # Momentum
    df["roc_5"]  = close.pct_change(5)
    df["roc_10"] = close.pct_change(10)

    # Stochastic
    low14  = low.rolling(14).min()
    high14 = high.rolling(14).max()
    df["stoch_k"] = (close - low14) / (high14 - low14 + 1e-9)
    df["stoch_d"] = df["stoch_k"].rolling(3).mean()

    # Regime
    df["uptrend"]       = ((df["ema_9"] > df["ema_20"]).astype(float) +
                           (df["ema_20"] > df["ema_50"]).astype(float))
    df["volatility_20"] = df["log_returns"].rolling(20).std()

    return df.dropna().reset_index(drop=True)


def get_feature_columns() -> List[str]:
    return [
        "returns", "log_returns", "hl_range", "oc_range",
        "price_vs_ema20", "price_vs_ema50", "ema9_vs_ema20", "ema20_vs_ema50", "ema9_slope",
        "rsi_14_norm", "rsi_oversold", "rsi_overbought",
        "macd_line_norm", "macd_hist_norm", "macd_above_sig",
        "bb_position", "bb_squeeze",
        "atr_14_norm",
        "vol_ratio", "vol_momentum", "obv_trend",
        "roc_5", "roc_10",
        "stoch_k", "stoch_d",
        "uptrend", "volatility_20",
    ]


def create_labels(df: pd.DataFrame, forward_bars: int = 5, threshold: float = 0.005) -> pd.Series:
    future_return = df["close"].shift(-forward_bars) / df["close"] - 1
    return (future_return > threshold).astype(int)
