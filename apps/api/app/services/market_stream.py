"""
Real-time market price engine: Redis-backed ticks with simulated walk or optional Binance public data.
"""
from __future__ import annotations

import asyncio
import json
import logging
import random
import threading
import time
import urllib.request
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import redis

from app.core.config import settings

logger = logging.getLogger(__name__)

REDIS_PREFIX = "omegabot:market"
LAST_TICK_GUARD = f"{REDIS_PREFIX}:last_tick_ts"
TICK_HASH = f"{REDIS_PREFIX}:tick"
BASE_HASH = f"{REDIS_PREFIX}:base"
SYMBOL_LIST_KEY = f"{REDIS_PREFIX}:symbols"

DEFAULT_BASE_PRICES: Dict[str, float] = {
    "RELIANCE": 2847.30,
    "TCS": 3912.60,
    "INFY": 1834.90,
    "HDFC": 1672.15,
    "NIFTY50": 24832.15,
    "BTCUSDT": 87432.00,
}

DEFAULT_SYMBOLS = ["RELIANCE", "TCS", "INFY"]

_redis_lock = threading.Lock()
_redis_client: Optional[redis.Redis] = None


def _get_redis() -> redis.Redis:
    global _redis_client
    with _redis_lock:
        if _redis_client is None:
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return _redis_client


def _candle_key(symbol: str) -> str:
    return f"{REDIS_PREFIX}:candles:{symbol.upper()}"


def _fetch_binance_btc() -> Optional[float]:
    """Public ticker; no API key required."""
    try:
        url = "https://api.binance.com/api/v3/ticker/price?symbol=BTCUSDT"
        with urllib.request.urlopen(url, timeout=3) as resp:
            data = json.loads(resp.read().decode())
            return float(data["price"])
    except Exception as e:
        logger.debug("Binance public fetch failed: %s", e)
        return None


def tick_symbol(symbol: str, exchange: str = "MOCK") -> float:
    """Advance one simulated (or external) tick and persist to Redis."""
    sym = symbol.upper()
    r = _get_redis()
    raw_base = r.hget(BASE_HASH, sym)
    base = float(raw_base) if raw_base is not None else DEFAULT_BASE_PRICES.get(sym, 1000.0)

    if sym == "BTCUSDT":
        ext = _fetch_binance_btc()
        if ext is not None:
            price = round(ext, 2)
        else:
            price = round(base * (1 + random.uniform(-0.002, 0.002)), 2)
    else:
        price = round(base * (1 + random.uniform(-0.002, 0.002)), 2)

    r.hset(BASE_HASH, sym, str(price))
    payload = {
        "symbol": sym,
        "price": price,
        "exchange": exchange,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r.hset(TICK_HASH, sym, json.dumps(payload))
    r.lpush(_candle_key(sym), str(price))
    r.ltrim(_candle_key(sym), 0, 99)
    r.sadd(SYMBOL_LIST_KEY, sym)
    return price


def tick_all_symbols_internal() -> Dict[str, float]:
    r = _get_redis()
    members = r.smembers(SYMBOL_LIST_KEY)
    symbols = sorted(members) if members else list(DEFAULT_SYMBOLS)
    out: Dict[str, float] = {}
    for sym in symbols:
        try:
            out[sym] = tick_symbol(sym)
        except Exception:
            logger.exception("tick_symbol failed for %s", sym)
    return out


def refresh_prices() -> None:
    """Refresh all symbols; deduped so API loop + Celery do not double-tick too fast."""
    r = _get_redis()
    now = time.time()
    raw = r.get(LAST_TICK_GUARD)
    if raw is not None:
        try:
            if now - float(raw) < 0.35:
                return
        except ValueError:
            pass
    tick_all_symbols_internal()
    r.set(LAST_TICK_GUARD, str(now))


def get_latest_price(symbol: str) -> Optional[Dict[str, Any]]:
    """Return latest tick dict (symbol, price, exchange, timestamp) or None."""
    sym = symbol.upper()
    raw = _get_redis().hget(TICK_HASH, sym)
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def get_last_closes(symbol: str, n: int = 20) -> List[float]:
    """Close prices in chronological order (oldest first)."""
    items = _get_redis().lrange(_candle_key(symbol.upper()), 0, max(0, n - 1))
    if not items:
        return []
    return [float(x) for x in reversed(items)]


def seed_market_prices_if_empty() -> None:
    """Ensure default symbols have at least one tick in Redis."""
    r = _get_redis()
    for sym in DEFAULT_SYMBOLS:
        if not r.hexists(TICK_HASH, sym):
            try:
                tick_symbol(sym)
            except Exception:
                logger.exception("seed tick failed for %s", sym)


async def start_market_stream() -> None:
    """
    Background loop for the API process: keeps Redis prices fresh.
    Celery `fetch_market_data` also calls `refresh_prices`; dedup prevents double work.
    """
    while True:
        try:
            await asyncio.to_thread(refresh_prices)
        except Exception:
            logger.exception("market stream tick failed")
        await asyncio.sleep(1.5)


def get_price_from_redis(symbol: str) -> float:
    """Get last price from Redis; return 0.0 if unavailable."""
    try:
        import redis as _redis
        from app.core.config import settings
        r = _redis.from_url(settings.REDIS_URL, decode_responses=True)
        val = r.hget(TICK_HASH, symbol.upper())
        if val:
            import json
            d = json.loads(val)
            return float(d.get("price", 0.0))
    except Exception:
        pass
    return 0.0
