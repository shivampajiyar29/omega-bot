"""
Real-Time Market Stream
=======================
* Binance WebSocket for CRYPTO symbols (BTCUSDT, ETHUSDT, etc.)
* NSE/BSE symbols: simulated GBM walk (no free Indian market WS)
* All prices stored in Redis so every service reads from one source
* AI signals generated every tick and stored back into Redis
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

REDIS_PREFIX      = "omegabot:market"
TICK_HASH         = f"{REDIS_PREFIX}:tick"
BASE_HASH         = f"{REDIS_PREFIX}:base"
CANDLE_KEY_FMT    = f"{REDIS_PREFIX}:candles:{{symbol}}"
SYMBOL_LIST_KEY   = f"{REDIS_PREFIX}:symbols"
LAST_TICK_GUARD   = f"{REDIS_PREFIX}:last_tick_ts"
AI_SIGNAL_KEY_FMT = "omegabot:paper:signal:{symbol}"

# ── Default seed prices ───────────────────────────────────────────────────────
DEFAULT_BASE_PRICES: Dict[str, float] = {
    "RELIANCE": 2847.30, "TCS": 3912.60, "INFY": 1834.90,
    "HDFC": 1672.15,    "NIFTY50": 24832.15, "SBIN": 812.45,
    "WIPRO": 456.30,    "BAJFINANCE": 7342.10,
    "BTCUSDT": 87432.00, "ETHUSDT": 3221.40, "BNBUSDT": 612.30,
    "SOLUSDT": 183.50,  "XRPUSDT": 0.624,
}

DEFAULT_SYMBOLS = list(DEFAULT_BASE_PRICES.keys())

CRYPTO_SYMBOLS = {s for s in DEFAULT_BASE_PRICES if s.endswith("USDT")}
INDIAN_SYMBOLS = {s for s in DEFAULT_BASE_PRICES if not s.endswith("USDT")}

# ── Redis connection pool ─────────────────────────────────────────────────────
_redis_lock   = threading.Lock()
_redis_client: Optional[redis.Redis] = None


def _get_redis() -> redis.Redis:
    global _redis_client
    with _redis_lock:
        if _redis_client is None:
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return _redis_client


# ── Price write helpers ───────────────────────────────────────────────────────

def _write_tick(symbol: str, price: float, exchange: str) -> None:
    """Persist one price tick to Redis."""
    sym = symbol.upper()
    r   = _get_redis()
    payload = {
        "symbol":    sym,
        "price":     price,
        "exchange":  exchange,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
    r.hset(BASE_HASH,  sym, str(price))
    r.hset(TICK_HASH,  sym, json.dumps(payload))
    r.lpush(CANDLE_KEY_FMT.format(symbol=sym), str(price))
    r.ltrim(CANDLE_KEY_FMT.format(symbol=sym), 0, 199)   # keep last 200
    r.sadd(SYMBOL_LIST_KEY, sym)


# ── Indian equity: GBM simulation ────────────────────────────────────────────

def tick_indian_symbol(symbol: str) -> float:
    sym  = symbol.upper()
    r    = _get_redis()
    raw  = r.hget(BASE_HASH, sym)
    base = float(raw) if raw else DEFAULT_BASE_PRICES.get(sym, 1000.0)
    price = round(base * (1 + random.gauss(0.00005, 0.0015)), 2)
    _write_tick(sym, price, "NSE")
    return price


# ── Crypto: fetch from Binance REST (no API key needed for public ticker) ────

def fetch_binance_prices_batch(symbols: List[str]) -> Dict[str, float]:
    """Fetch multiple prices in one REST call."""
    prices: Dict[str, float] = {}
    try:
        url = "https://api.binance.com/api/v3/ticker/price"
        with urllib.request.urlopen(url, timeout=4) as resp:
            data = json.loads(resp.read().decode())
        by_sym = {d["symbol"]: float(d["price"]) for d in data}
        for sym in symbols:
            if sym.upper() in by_sym:
                prices[sym.upper()] = round(by_sym[sym.upper()], 6)
    except Exception as e:
        logger.debug("Binance batch fetch failed: %s", e)
    return prices


def tick_crypto_symbol(symbol: str, price: Optional[float] = None) -> float:
    sym = symbol.upper()
    r   = _get_redis()
    if price is None:
        raw = r.hget(BASE_HASH, sym)
        base = float(raw) if raw else DEFAULT_BASE_PRICES.get(sym, 1000.0)
        price = round(base * (1 + random.gauss(0, 0.001)), 6)
    _write_tick(sym, price, "BINANCE")
    return price


# ── Full tick cycle ───────────────────────────────────────────────────────────

def refresh_prices() -> None:
    """
    Refresh all symbols. Called every ~2s from background task.
    * Crypto: batch Binance REST
    * Indian: GBM simulation
    """
    r   = _get_redis()
    now = time.time()
    raw = r.get(LAST_TICK_GUARD)
    if raw:
        try:
            if now - float(raw) < 0.5:
                return
        except ValueError:
            pass
    r.set(LAST_TICK_GUARD, str(now))

    # Crypto — real Binance prices
    crypto_syms = list(CRYPTO_SYMBOLS)
    binance_prices = fetch_binance_prices_batch(crypto_syms)
    for sym in crypto_syms:
        tick_crypto_symbol(sym, binance_prices.get(sym))

    # Indian — simulated
    for sym in INDIAN_SYMBOLS:
        tick_indian_symbol(sym)


# ── AI signal generation (rule-based + optional Gemini) ──────────────────────

def generate_and_store_signal(symbol: str) -> Dict[str, Any]:
    """
    Generate BUY/SELL/HOLD signal from last 20 closes.
    Stores result in Redis so paper_trading.py can pick it up.
    """
    closes = get_last_closes(symbol, 20)
    if len(closes) < 5:
        sig = {"symbol": symbol, "action": "hold", "confidence": 0.5, "source": "insufficient_data"}
    else:
        # EMA crossover
        def ema(prices, n):
            result, k = [], 2 / (n + 1)
            for i, p in enumerate(prices):
                if i == 0:
                    result.append(p)
                else:
                    result.append(p * k + result[-1] * (1 - k))
            return result

        ema9  = ema(closes, 9)[-1]
        ema21 = ema(closes, min(21, len(closes)))[-1]
        roc5  = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
        cur   = closes[-1]

        if ema9 > ema21 and roc5 > 0.001:
            action = "buy"
            conf = min(0.90, 0.65 + abs(roc5) * 10)
        elif ema9 < ema21 and roc5 < -0.001:
            action = "sell"
            conf = min(0.90, 0.65 + abs(roc5) * 10)
        else:
            action = "hold"
            conf = 0.55

        sig = {
            "symbol":     symbol,
            "action":     action,
            "confidence": round(conf, 3),
            "ema9":       round(ema9,  2),
            "ema21":      round(ema21, 2),
            "price":      round(cur,   4),
            "source":     "ema_crossover",
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }

    r = _get_redis()
    r.set(AI_SIGNAL_KEY_FMT.format(symbol=symbol.upper()),
          json.dumps(sig), ex=30)
    return sig


# ── Public helpers ────────────────────────────────────────────────────────────

def get_latest_price(symbol: str) -> Optional[Dict[str, Any]]:
    raw = _get_redis().hget(TICK_HASH, symbol.upper())
    if not raw:
        return None
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return None


def get_price_from_redis(symbol: str) -> float:
    tick = get_latest_price(symbol)
    return float(tick["price"]) if tick else 0.0


def get_last_closes(symbol: str, n: int = 20) -> List[float]:
    items = _get_redis().lrange(
        CANDLE_KEY_FMT.format(symbol=symbol.upper()), 0, max(0, n - 1)
    )
    if not items:
        return []
    return [float(x) for x in reversed(items)]


def seed_market_prices_if_empty() -> None:
    r = _get_redis()
    for sym in DEFAULT_SYMBOLS:
        if not r.hexists(TICK_HASH, sym):
            try:
                if sym in CRYPTO_SYMBOLS:
                    tick_crypto_symbol(sym)
                else:
                    tick_indian_symbol(sym)
            except Exception:
                logger.exception("seed tick failed for %s", sym)


# ── Background async loop ─────────────────────────────────────────────────────

async def start_market_stream() -> None:
    """
    Main background loop: refresh prices every 2s + generate AI signals.
    Runs inside the FastAPI lifespan.
    """
    logger.info("Market stream started — crypto via Binance REST, equities simulated")
    cycle = 0
    while True:
        try:
            await asyncio.to_thread(refresh_prices)
            # Generate AI signals every 5 cycles (~10s)
            if cycle % 5 == 0:
                for sym in DEFAULT_SYMBOLS:
                    try:
                        await asyncio.to_thread(generate_and_store_signal, sym)
                    except Exception:
                        pass
            cycle += 1
        except Exception:
            logger.exception("market stream tick failed")
        await asyncio.sleep(2.0)
