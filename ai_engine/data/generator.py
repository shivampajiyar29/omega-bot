"""Synthetic OHLCV generator for model training."""
from __future__ import annotations
import math, random
from datetime import datetime, timedelta
from typing import List, Dict


def generate_synthetic_ohlcv(n_bars: int = 2000, seed: int = 42,
                              start_price: float = 2800.0) -> List[Dict]:
    rng = random.Random(seed)
    REGIMES = [
        {"drift": 0.0003,  "vol": 0.010},
        {"drift": -0.0002, "vol": 0.010},
        {"drift": 0.00005, "vol": 0.008},
        {"drift": 0.0001,  "vol": 0.022},
    ]
    bars, price = [], start_price
    start = datetime(2023, 1, 1, 9, 15)
    for i in range(n_bars):
        r = REGIMES[(i // 250) % len(REGIMES)]
        shock = rng.gauss(0, 1)
        log_ret = (r["drift"] - 0.5 * r["vol"] ** 2) + r["vol"] * shock
        price = max(price * math.exp(log_ret), 1.0)
        op = (bars[-1]["close"] if bars else price) * (1 + rng.gauss(0, 0.002))
        hi = max(op, price) * (1 + abs(rng.gauss(0, 0.003)))
        lo = min(op, price) * (1 - abs(rng.gauss(0, 0.003)))
        vol = rng.randint(100_000, 500_000)
        bars.append({
            "time":   (start + timedelta(minutes=15 * i)).isoformat(),
            "open":   round(op, 2), "high": round(hi, 2),
            "low":    round(lo, 2), "close": round(price, 2),
            "volume": vol,
        })
    return bars
