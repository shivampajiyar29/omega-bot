"""
DSL Evaluator — converts strategy JSON DSL to a signal function.
Works with the BacktestEngine.
"""
from __future__ import annotations
import logging
from typing import Any, Callable, Dict, List, Optional

import numpy as np
import pandas as pd

from app.backtester.engine import Bar

logger = logging.getLogger(__name__)


def _ema(series: pd.Series, period: int) -> pd.Series:
    return series.ewm(span=period, adjust=False).mean()


def _rsi(series: pd.Series, period: int = 14) -> pd.Series:
    delta = series.diff()
    gain = delta.clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    loss = (-delta).clip(lower=0).ewm(com=period - 1, adjust=False).mean()
    rs = gain / (loss + 1e-9)
    return 100 - (100 / (1 + rs))


def _macd(series: pd.Series, fast=12, slow=26, signal=9):
    ema_fast = _ema(series, fast)
    ema_slow = _ema(series, slow)
    macd_line = ema_fast - ema_slow
    signal_line = _ema(macd_line, signal)
    histogram = macd_line - signal_line
    return macd_line, signal_line, histogram


def _compute_indicators(df: pd.DataFrame, indicators: List[Dict]) -> Dict[str, pd.Series]:
    close = df["close"]
    result: Dict[str, pd.Series] = {}

    for ind in indicators:
        ind_id = ind.get("id", "")
        ind_type = ind.get("type", "")
        params = ind.get("params", {})

        try:
            if ind_type == "ema":
                result[ind_id] = _ema(close, params.get("period", 20))
            elif ind_type == "sma":
                result[ind_id] = close.rolling(params.get("period", 20)).mean()
            elif ind_type == "rsi":
                result[ind_id] = _rsi(close, params.get("period", 14))
            elif ind_type == "macd":
                line, sig, hist = _macd(close, params.get("fast", 12), params.get("slow", 26), params.get("signal", 9))
                result[f"{ind_id}_line"] = line
                result[f"{ind_id}_signal"] = sig
                result[f"{ind_id}_histogram"] = hist
                result[ind_id] = line
            elif ind_type == "bbands":
                period = params.get("period", 20)
                std_dev = params.get("std", 2)
                mid = close.rolling(period).mean()
                std = close.rolling(period).std()
                result[f"{ind_id}_upper"] = mid + std_dev * std
                result[f"{ind_id}_mid"] = mid
                result[f"{ind_id}_lower"] = mid - std_dev * std
                result[ind_id] = mid
            elif ind_type == "atr":
                period = params.get("period", 14)
                high, low = df["high"], df["low"]
                tr = pd.concat([
                    high - low,
                    (high - close.shift()).abs(),
                    (low - close.shift()).abs(),
                ], axis=1).max(axis=1)
                result[ind_id] = tr.ewm(com=period - 1, adjust=False).mean()
            elif ind_type == "price":
                result[ind_id] = close
            elif ind_type == "volume":
                result[ind_id] = df["volume"]
            elif ind_type == "vwap":
                tp = (df["high"] + df["low"] + df["close"]) / 3
                result[ind_id] = (tp * df["volume"]).cumsum() / df["volume"].cumsum()
        except Exception as e:
            logger.debug(f"Indicator {ind_id} compute failed: {e}")

    return result


def _get_value(ref: Dict, computed: Dict[str, pd.Series], i: int) -> Optional[float]:
    if "value" in ref:
        return float(ref["value"])
    ind_id = ref.get("indicator_id", "")
    field_name = ref.get("field", "")
    key = f"{ind_id}_{field_name}" if field_name else ind_id
    series = computed.get(key)
    if series is None or i >= len(series):
        return None
    v = series.iloc[i]
    return None if pd.isna(v) else float(v)


def _eval_condition(cond: Dict, computed: Dict[str, pd.Series], i: int) -> bool:
    left = _get_value(cond.get("left", {}), computed, i)
    right = _get_value(cond.get("right", {}), computed, i)
    op = cond.get("operator", "gt")

    if left is None or right is None:
        return False

    if op == "gt":   return left > right
    if op == "gte":  return left >= right
    if op == "lt":   return left < right
    if op == "lte":  return left <= right
    if op == "eq":   return abs(left - right) < 1e-9
    if op == "neq":  return abs(left - right) >= 1e-9

    # Crossover operators need previous bar
    if i < 1:
        return False
    left_prev = _get_value(cond.get("left", {}), computed, i - 1)
    right_prev = _get_value(cond.get("right", {}), computed, i - 1)
    if left_prev is None or right_prev is None:
        return False

    if op == "crosses_above":
        return left_prev <= right_prev and left > right
    if op == "crosses_below":
        return left_prev >= right_prev and left < right
    return False


def _eval_group(group: Dict, computed: Dict[str, pd.Series], i: int) -> bool:
    logic = group.get("logic", "and").lower()
    conditions = group.get("conditions", [])
    results = [_eval_condition(c, computed, i) for c in conditions]
    return all(results) if logic == "and" else any(results)


class DSLEvaluator:
    """Converts a strategy DSL dict into a callable signal function."""

    def __init__(self, dsl: Dict):
        self.dsl = dsl or {}
        self.indicators_config = dsl.get("indicators", [])
        self.entry = dsl.get("entry", {})
        self.exits = dsl.get("exits", [])
        self.allow_short = dsl.get("allow_short", False)

    def evaluate(self, bars: List[Bar], position, params) -> Optional[str]:
        if len(bars) < 30:
            return None

        df = pd.DataFrame([{
            "open": b.open, "high": b.high, "low": b.low,
            "close": b.close, "volume": b.volume,
        } for b in bars])

        computed = _compute_indicators(df, self.indicators_config)
        i = len(df) - 1

        # ── Check exits ───────────────────────────────────────────────────────
        if position is not None:
            for ex in self.exits:
                etype = ex.get("type", "")
                if etype == "fixed_stop":
                    ep = position.get("entry_price", 0)
                    val = ex.get("value", 1.5) / 100
                    current = df["close"].iloc[i]
                    if position.get("side") == "long" and current < ep * (1 - val):
                        return "exit"
                    if position.get("side") == "short" and current > ep * (1 + val):
                        return "exit"
                elif etype == "fixed_target":
                    ep = position.get("entry_price", 0)
                    val = ex.get("value", 3.0) / 100
                    current = df["close"].iloc[i]
                    if position.get("side") == "long" and current > ep * (1 + val):
                        return "exit"
                    if position.get("side") == "short" and current < ep * (1 - val):
                        return "exit"
                elif etype == "indicator_signal":
                    sig_group = ex.get("indicator_signal", {})
                    if sig_group and _eval_group(sig_group, computed, i):
                        return "exit"

        # ── Check entries ────────────────────────────────────────────────────
        if position is None:
            long_entry = self.entry.get("long", {})
            if long_entry and _eval_group(long_entry, computed, i):
                return "long"

            if self.allow_short:
                short_entry = self.entry.get("short", {})
                if short_entry and _eval_group(short_entry, computed, i):
                    return "short"

        return None

    def get_signal_fn(self) -> Callable:
        def fn(bars, position, params):
            return self.evaluate(bars, position, params)
        return fn
