"""
Real-Time Market Stream
=======================
* Binance REST polling for CRYPTO (real prices every 2s)
* Indian equities: GBM simulation (no free real-time NSE feed)
* Prices stored in Redis → consumed by WebSocket, paper_trading, bot loops
* AI signals generated every 10s and stored in Redis
"""
from __future__ import annotations

import asyncio
import json
import logging
import math
import random
import threading
import time
import urllib.request
import urllib.error
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

# ── Seed prices ───────────────────────────────────────────────────────────────
DEFAULT_BASE_PRICES: Dict[str, float] = {
    "RELIANCE": 2847.30, "TCS": 3912.60, "INFY": 1834.90,
    "HDFC": 1672.15,     "NIFTY50": 24832.15, "SBIN": 812.45,
    "WIPRO": 456.30,     "BAJFINANCE": 7342.10,
    "BTCUSDT": 87432.00, "ETHUSDT": 3221.40, "BNBUSDT": 612.30,
    "SOLUSDT": 183.50,   "XRPUSDT": 0.624,
}

DEFAULT_SYMBOLS = list(DEFAULT_BASE_PRICES.keys())
CRYPTO_SYMBOLS  = {s for s in DEFAULT_BASE_PRICES if s.endswith("USDT")}
INDIAN_SYMBOLS  = {s for s in DEFAULT_BASE_PRICES if not s.endswith("USDT")}

# ── Redis connection ──────────────────────────────────────────────────────────
_redis_lock:   threading.Lock          = threading.Lock()
_redis_client: Optional[redis.Redis]  = None


def _get_redis() -> redis.Redis:
    global _redis_client
    with _redis_lock:
        if _redis_client is None:
            _redis_client = redis.from_url(settings.REDIS_URL, decode_responses=True)
        return _redis_client


# ── Price write ───────────────────────────────────────────────────────────────

def _write_tick(symbol: str, price: float, exchange: str) -> None:
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
    r.ltrim(CANDLE_KEY_FMT.format(symbol=sym), 0, 299)   # keep 300 candles
    r.sadd(SYMBOL_LIST_KEY, sym)


# ── Binance REST (real crypto prices) ────────────────────────────────────────

def fetch_binance_prices_batch(symbols: List[str]) -> Dict[str, float]:
    """Fetch current prices from Binance public REST API."""
    if not symbols:
        return {}
    try:
        syms_param = json.dumps([s.upper() for s in symbols])
        url = f"https://api.binance.com/api/v3/ticker/price?symbols={urllib.request.quote(syms_param)}"
        req = urllib.request.Request(url, headers={"User-Agent": "OmegaBot/1.0"})
        with urllib.request.urlopen(req, timeout=5) as resp:
            data = json.loads(resp.read())
        return {item["symbol"]: float(item["price"]) for item in data}
    except Exception as e:
        logger.debug("Binance batch fetch failed: %s", e)
        return {}


def tick_crypto_symbol(symbol: str, real_price: Optional[float] = None) -> float:
    """Update crypto symbol with real Binance price or GBM simulation."""
    r     = _get_redis()
    sym   = symbol.upper()
    base  = float(r.hget(BASE_HASH, sym) or DEFAULT_BASE_PRICES.get(sym, 1.0))

    if real_price and real_price > 0:
        price = real_price
    else:
        # GBM simulation as fallback
        vol   = 0.003
        drift = 0.00005
        shock = random.gauss(0, 1)
        price = base * math.exp(drift + vol * shock)

    _write_tick(sym, round(price, 6), "BINANCE")
    return price


def tick_indian_symbol(symbol: str) -> float:
    """Simulate Indian equity price using GBM (no free real-time NSE feed)."""
    r    = _get_redis()
    sym  = symbol.upper()
    base = float(r.hget(BASE_HASH, sym) or DEFAULT_BASE_PRICES.get(sym, 1000.0))
    vol  = 0.002
    drift = 0.00003
    price = base * math.exp(drift + vol * random.gauss(0, 1))
    _write_tick(sym, round(price, 2), "NSE")
    return price


# ── Price read ────────────────────────────────────────────────────────────────

def get_latest_price(symbol: str) -> Optional[Dict[str, Any]]:
    try:
        r   = _get_redis()
        raw = r.hget(TICK_HASH, symbol.upper())
        return json.loads(raw) if raw else None
    except Exception:
        return None


def get_price_from_redis(symbol: str) -> float:
    tick = get_latest_price(symbol)
    return float(tick["price"]) if tick else 0.0


def get_last_closes(symbol: str, n: int = 30) -> List[float]:
    try:
        r    = _get_redis()
        vals = r.lrange(CANDLE_KEY_FMT.format(symbol=symbol.upper()), 0, n - 1)
        return [float(v) for v in reversed(vals) if v]
    except Exception:
        return []


def get_all_prices() -> Dict[str, Dict]:
    try:
        r    = _get_redis()
        raw  = r.hgetall(TICK_HASH)
        out  = {}
        for sym, val in raw.items():
            try:
                out[sym] = json.loads(val)
            except Exception:
                pass
        return out
    except Exception:
        return {}


# ── AI signal generation ──────────────────────────────────────────────────────

def generate_and_store_signal(symbol: str) -> Dict[str, Any]:
    """EMA crossover signal — stored in Redis for paper trading."""
    closes = get_last_closes(symbol, 30)
    if len(closes) < 5:
        sig = {"symbol": symbol, "action": "hold", "confidence": 0.5,
               "reasoning": "Insufficient data", "source": "rule", "price": 0}
    else:
        def ema(prices: List[float], n: int) -> List[float]:
            result, k = [], 2 / (n + 1)
            for i, p in enumerate(prices):
                result.append(p if i == 0 else p * k + result[-1] * (1 - k))
            return result

        ema9  = ema(closes, 9)[-1]
        ema21 = ema(closes, min(21, len(closes)))[-1]
        roc5  = (closes[-1] - closes[-5]) / closes[-5] if len(closes) >= 5 else 0
        cur   = closes[-1]

        if ema9 > ema21 and roc5 > 0.001:
            action = "buy"
            conf   = min(0.90, 0.65 + abs(roc5) * 10)
            reason = f"EMA9 ({ema9:.2f}) > EMA21 ({ema21:.2f}), ROC={roc5*100:.2f}%"
        elif ema9 < ema21 and roc5 < -0.001:
            action = "sell"
            conf   = min(0.90, 0.65 + abs(roc5) * 10)
            reason = f"EMA9 ({ema9:.2f}) < EMA21 ({ema21:.2f}), ROC={roc5*100:.2f}%"
        else:
            action = "hold"
            conf   = 0.55
            reason = "No clear crossover signal"

        sig = {
            "symbol":     symbol,
            "action":     action,
            "confidence": round(conf, 3),
            "reasoning":  reason,
            "source":     "rule_ema",
            "price":      round(cur, 4),
            "timestamp":  datetime.now(timezone.utc).isoformat(),
        }

    try:
        _get_redis().set(
            AI_SIGNAL_KEY_FMT.format(symbol=symbol.upper()),
            json.dumps(sig), ex=120
        )
    except Exception as e:
        logger.debug("Signal store failed: %s", e)

    return sig


# ── Seed initial prices ───────────────────────────────────────────────────────

def seed_market_prices_if_empty() -> None:
    """Write seed prices to Redis on startup if empty."""
    try:
        r = _get_redis()
        existing = r.hgetall(TICK_HASH)
        if not existing:
            logger.info("Seeding initial market prices to Redis…")
            for sym, price in DEFAULT_BASE_PRICES.items():
                exchange = "BINANCE" if sym.endswith("USDT") else "NSE"
                _write_tick(sym, price, exchange)
            logger.info("Market prices seeded: %d symbols", len(DEFAULT_BASE_PRICES))
    except Exception as e:
        logger.warning("Could not seed prices (Redis offline?): %s", e)


def refresh_prices() -> None:
    """Refresh all prices. Called every 2s from background task."""
    # Rate-limit guard
    r   = _get_redis()
    now = time.time()
    raw = r.get(LAST_TICK_GUARD)
    if raw:
        try:
            if now - float(raw) < 1.0:
                return
        except ValueError:
            pass
    r.set(LAST_TICK_GUARD, str(now), ex=10)

    # Crypto — real Binance prices
    crypto_syms    = list(CRYPTO_SYMBOLS)
    binance_prices = fetch_binance_prices_batch(crypto_syms)
    for sym in crypto_syms:
        tick_crypto_symbol(sym, binance_prices.get(sym))

    # Indian — simulated
    for sym in INDIAN_SYMBOLS:
        tick_indian_symbol(sym)


# ── Background stream (runs inside FastAPI lifespan) ─────────────────────────

async def start_market_stream() -> None:
    """
    Main background loop: refresh prices every 2s + AI signals every 10s.
    """
    logger.info("Market stream starting — Binance REST for crypto, GBM for Indian equities")
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
        except asyncio.CancelledError:
            logger.info("Market stream stopped")
            break
        except Exception:
            logger.exception("Market stream tick failed")
        await asyncio.sleep(2.0)
