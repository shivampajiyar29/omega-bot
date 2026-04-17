"""
AI Trading Strategy Service
============================
Uses Google Gemini (primary) to generate BUY/SELL/HOLD signals with reasoning.
Falls back to EMA-crossover rule-based logic if Gemini is unavailable.

Signal is stored in Redis and consumed by paper_trading.py.
"""
from __future__ import annotations

import json
import logging
from typing import Any, Dict, List, Optional

from app.core.config import settings

logger = logging.getLogger(__name__)

# ── Gemini AI signal ──────────────────────────────────────────────────────────

async def _call_gemini(prompt: str) -> Optional[str]:
    """Call Gemini 1.5 Flash REST API."""
    if not settings.GEMINI_API_KEY:
        return None
    try:
        import httpx
        url = (
            f"https://generativelanguage.googleapis.com/v1beta/models/"
            f"gemini-1.5-flash:generateContent?key={settings.GEMINI_API_KEY}"
        )
        payload = {
            "contents": [{"parts": [{"text": prompt}]}],
            "generationConfig": {"maxOutputTokens": 200, "temperature": 0.1},
        }
        async with httpx.AsyncClient(timeout=8.0) as client:
            r = await client.post(url, json=payload)
            r.raise_for_status()
            data = r.json()
            return data["candidates"][0]["content"]["parts"][0]["text"]
    except Exception as e:
        logger.debug("Gemini call failed: %s", e)
        return None


async def get_ai_signal(symbol: str, closes: List[float]) -> Dict[str, Any]:
    """
    Generate AI signal for a symbol.
    Returns: {symbol, action, confidence, reasoning, source}
    """
    if len(closes) < 5:
        return {"symbol": symbol, "action": "hold", "confidence": 0.5,
                "reasoning": "Insufficient data", "source": "rule"}

    cur      = closes[-1]
    prev5    = closes[-5]
    roc      = (cur - prev5) / prev5 * 100
    hi20     = max(closes[-20:]) if len(closes) >= 20 else max(closes)
    lo20     = min(closes[-20:]) if len(closes) >= 20 else min(closes)

    # ── Try Gemini ───────────────────────────────────────────────────────────
    prompt = f"""You are a quantitative trading analyst.
Symbol: {symbol}
Last price: {cur:.4f}
5-bar return: {roc:.2f}%
20-bar high: {hi20:.4f}, low: {lo20:.4f}
Last 10 closes: {[round(c, 4) for c in closes[-10:]]}

Respond ONLY with valid JSON like:
{{"action":"buy","confidence":0.78,"reasoning":"Brief 1-sentence reason"}}
action must be one of: buy, sell, hold
confidence: 0.50 to 0.95"""

    raw = await _call_gemini(prompt)
    if raw:
        try:
            raw = raw.strip()
            if "```" in raw:
                raw = raw.split("```")[1].replace("json","").strip()
            data = json.loads(raw)
            action = str(data.get("action", "hold")).lower()
            if action not in ("buy", "sell", "hold"):
                action = "hold"
            return {
                "symbol":     symbol,
                "action":     action,
                "confidence": float(data.get("confidence", 0.65)),
                "reasoning":  str(data.get("reasoning", "")),
                "source":     "gemini",
                "price":      cur,
            }
        except Exception as e:
            logger.debug("Gemini response parse failed: %s | raw=%s", e, raw)

    # ── Rule-based fallback ─────────────────────────────────────────────────
    return _rule_based_signal(symbol, closes, cur, roc)


def _rule_based_signal(symbol: str, closes: List[float],
                       cur: float, roc: float) -> Dict[str, Any]:
    """EMA crossover + momentum rule-based signal."""
    def ema(prices: List[float], n: int) -> float:
        k = 2 / (n + 1)
        v = prices[0]
        for p in prices[1:]:
            v = p * k + v * (1 - k)
        return v

    e9  = ema(closes[-9:],  9)  if len(closes) >= 9  else cur
    e21 = ema(closes[-21:], 21) if len(closes) >= 21 else cur

    if e9 > e21 and roc > 0.1:
        action, conf, reason = "buy",  min(0.88, 0.62 + abs(roc) * 0.08), "EMA9 > EMA21, positive momentum"
    elif e9 < e21 and roc < -0.1:
        action, conf, reason = "sell", min(0.88, 0.62 + abs(roc) * 0.08), "EMA9 < EMA21, negative momentum"
    else:
        action, conf, reason = "hold", 0.55, "No clear trend"

    return {
        "symbol":     symbol,
        "action":     action,
        "confidence": round(conf, 3),
        "reasoning":  reason,
        "source":     "rule_ema",
        "price":      cur,
    }


# ── Legacy sync interface (used by Celery tasks) ──────────────────────────────

def generate_signal(symbol: str, candles: List[float]) -> Dict[str, Any]:
    """Sync version for backward compatibility."""
    return _rule_based_signal(symbol, candles, candles[-1] if candles else 0,
                              (candles[-1] - candles[-5]) / candles[-5] * 100
                              if len(candles) >= 5 else 0)
