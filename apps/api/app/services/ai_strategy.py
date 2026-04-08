"""
Rule-based trading signals (simple momentum on last 3 closes). Replace with ML later.
"""
from typing import Any, Dict, List


def generate_signal(symbol: str, candles: List[float]) -> Dict[str, Any]:
    """
    If last 3 closes strictly increase -> BUY.
    If last 3 strictly decrease -> SELL.
    Else HOLD.
    """
    if len(candles) < 3:
        return {"symbol": symbol, "action": "hold", "confidence": 0.6}

    a, b, c = candles[-3], candles[-2], candles[-1]
    if a < b < c:
        momentum = (c - a) / max(a, 1e-9)
        conf = 0.65 + min(0.25, momentum * 2.0)
        return {"symbol": symbol, "action": "buy", "confidence": round(min(0.9, conf), 2)}

    if a > b > c:
        momentum = (a - c) / max(c, 1e-9)
        conf = 0.65 + min(0.25, momentum * 2.0)
        return {"symbol": symbol, "action": "sell", "confidence": round(min(0.9, conf), 2)}

    return {"symbol": symbol, "action": "hold", "confidence": 0.65}
