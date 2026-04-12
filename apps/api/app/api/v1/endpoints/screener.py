"""Screener API — multi-symbol signal scanner."""
import asyncio
import logging
from typing import Optional
from fastapi import APIRouter, Query

log = logging.getLogger(__name__)
router = APIRouter()

DEFAULT_SYMBOLS = [
    ("RELIANCE", "NSE"), ("TCS", "NSE"), ("INFY", "NSE"),
    ("HDFC", "NSE"), ("BTCUSDT", "BINANCE"), ("ETHUSDT", "BINANCE"),
    ("NIFTY50", "NSE"), ("WIPRO", "NSE"),
]


async def _scan_one(symbol: str, exchange: str, timeframe: str) -> dict:
    from app.services.ai_engine_client import get_ai_signal
    from app.adapters.marketdata.mock_data import MockMarketDataAdapter
    from datetime import datetime, timedelta
    try:
        adapter = MockMarketDataAdapter()
        await adapter.connect()
        bars = await adapter.get_historical_ohlcv(
            symbol, exchange, timeframe,
            datetime.utcnow() - timedelta(days=30), datetime.utcnow(),
        )
        ohlcv = [{"open": b.open, "high": b.high, "low": b.low,
                  "close": b.close, "volume": b.volume} for b in bars]
        result = await get_ai_signal(symbol, ohlcv, exchange, timeframe)
        if result:
            return {**result, "symbol": symbol, "exchange": exchange, "available": True}
        # Technical fallback
        if len(bars) >= 21:
            closes = [b.close for b in bars]
            ema9 = closes[-1]
            ema21 = sum(closes[-21:]) / 21
            chg = (closes[-1] - closes[-14]) / closes[-14] * 100
            if ema9 > ema21 and chg > 0:
                return {"symbol": symbol, "exchange": exchange, "signal": "BUY",
                        "confidence": 0.55, "agreement": False, "available": False}
            elif ema9 < ema21 and chg < 0:
                return {"symbol": symbol, "exchange": exchange, "signal": "SELL",
                        "confidence": 0.55, "agreement": False, "available": False}
    except Exception as e:
        log.debug(f"scan {symbol}: {e}")
    return {"symbol": symbol, "exchange": exchange, "signal": "HOLD",
            "confidence": 0.0, "agreement": False, "available": False}


@router.get("/scan")
async def scan(symbols: Optional[str] = None, exchange: str = "NSE",
               timeframe: str = Query("15m"), limit: int = Query(20)):
    pairs = [(s.strip().upper(), exchange) for s in symbols.split(",")] \
        if symbols else DEFAULT_SYMBOLS[:limit]
    tasks = [_scan_one(sym, exc, timeframe) for sym, exc in pairs]
    results = await asyncio.gather(*tasks, return_exceptions=False)
    def sort_key(r):
        return ({"BUY": 0, "SELL": 1, "HOLD": 2}.get(r.get("signal", "HOLD"), 2), -r.get("confidence", 0))
    return sorted([r for r in results if isinstance(r, dict)], key=sort_key)[:limit]


@router.get("/universe")
async def universe():
    return [{"symbol": s, "exchange": e} for s, e in DEFAULT_SYMBOLS]


@router.get("/top-signals")
async def top_signals(timeframe: str = Query("15m")):
    results = await scan(timeframe=timeframe, limit=10)
    return {
        "top_buys":  [r for r in results if r.get("signal") == "BUY"][:3],
        "top_sells": [r for r in results if r.get("signal") == "SELL"][:3],
        "ai_available": any(r.get("available") for r in results),
    }
