"""
Market Data API — OHLCV data, instrument search, live quotes.
Uses Binance public market data for live/paper workflows.
"""
from typing import List, Optional
from datetime import datetime, timedelta, timezone

import aiohttp
from fastapi import APIRouter, Query, HTTPException

router = APIRouter()

BINANCE_REST = "https://api.binance.com/api/v3"


@router.get("/search", response_model=List[dict])
async def search_instruments(
    q: str = Query(..., min_length=1, description="Symbol or name to search"),
    market_type: str = "equity",
):
    """Search for tradeable instruments by symbol or name."""
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as s:
        async with s.get(f"{BINANCE_REST}/exchangeInfo") as r:
            if r.status >= 400:
                raise HTTPException(status_code=503, detail="Binance exchange info unavailable")
            data = await r.json()
    q_up = q.upper()
    out = []
    for item in data.get("symbols", []):
        sym = item.get("symbol", "")
        base = item.get("baseAsset", "")
        quote = item.get("quoteAsset", "")
        if q_up in sym or q_up in base:
            out.append(
                {
                    "symbol": sym,
                    "name": f"{base}/{quote}",
                    "exchange": "BINANCE",
                    "type": "crypto",
                }
            )
        if len(out) >= 100:
            break
    return out


@router.get("/ohlcv", response_model=List[dict])
async def get_ohlcv(
    symbol: str,
    exchange: str = "NSE",
    timeframe: str = "15m",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 200,
):
    """
    Fetch OHLCV bars for a symbol.
    Returns data from the active market data connector.
    Falls back to mock data if no real connector is configured.
    """
    sym = _normalize_binance_symbol(symbol)
    interval = _binance_interval(timeframe)
    if not interval:
        raise HTTPException(status_code=400, detail=f"Unsupported timeframe for Binance: {timeframe}")

    end = datetime.fromisoformat(to_date) if to_date else datetime.now(timezone.utc)
    if from_date:
        start = datetime.fromisoformat(from_date)
    else:
        interval_mins = _timeframe_minutes(timeframe)
        start = end - timedelta(minutes=interval_mins * limit)

    params = {
        "symbol": sym,
        "interval": interval,
        "startTime": int(start.timestamp() * 1000),
        "endTime": int(end.timestamp() * 1000),
        "limit": min(max(limit, 1), 1000),
    }
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=25)) as s:
        async with s.get(f"{BINANCE_REST}/klines", params=params) as r:
            txt = await r.text()
            if r.status >= 400:
                raise HTTPException(status_code=503, detail=f"Binance klines failed: {txt[:200]}")
            rows = await r.json()

    out = []
    for k in rows:
        out.append(
            {
                "t": datetime.fromtimestamp(k[0] / 1000, tz=timezone.utc).isoformat(),
                "o": float(k[1]),
                "h": float(k[2]),
                "l": float(k[3]),
                "c": float(k[4]),
                "v": float(k[5]),
            }
        )
    return out[-limit:]


@router.get("/quote/{symbol}", response_model=dict)
async def get_quote(symbol: str, exchange: str = "NSE"):
    """Get current price quote for a symbol."""
    sym = _normalize_binance_symbol(symbol)
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=15)) as s:
        async with s.get(f"{BINANCE_REST}/ticker/price", params={"symbol": sym}) as r:
            txt = await r.text()
            if r.status >= 400:
                raise HTTPException(status_code=503, detail=f"Binance quote failed: {txt[:200]}")
            payload = await r.json()
    price = float(payload.get("price", 0.0))

    return {
        "symbol":    symbol,
        "exchange":  "BINANCE",
        "price":     price,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/indices", response_model=List[dict])
async def get_indices():
    """Return current major index values."""
    pairs = ["BTCUSDT", "ETHUSDT", "BNBUSDT", "SOLUSDT", "XRPUSDT"]
    async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=20)) as s:
        async with s.get(f"{BINANCE_REST}/ticker/24hr") as r:
            if r.status >= 400:
                raise HTTPException(status_code=503, detail="Binance 24hr ticker unavailable")
            data = await r.json()
    by_symbol = {x.get("symbol"): x for x in data if x.get("symbol") in pairs}
    out = []
    for p in pairs:
        d = by_symbol.get(p)
        if not d:
            continue
        out.append(
            {
                "symbol": p,
                "price": float(d.get("lastPrice", 0.0)),
                "change": float(d.get("priceChange", 0.0)),
                "change_pct": float(d.get("priceChangePercent", 0.0)),
            }
        )
    return out


@router.get("/timeframes", response_model=List[dict])
async def get_supported_timeframes():
    return [
        {"value": "1m",  "label": "1 Minute"},
        {"value": "3m",  "label": "3 Minutes"},
        {"value": "5m",  "label": "5 Minutes"},
        {"value": "15m", "label": "15 Minutes"},
        {"value": "30m", "label": "30 Minutes"},
        {"value": "1h",  "label": "1 Hour"},
        {"value": "2h",  "label": "2 Hours"},
        {"value": "4h",  "label": "4 Hours"},
        {"value": "1d",  "label": "Daily"},
        {"value": "1w",  "label": "Weekly"},
    ]


def _timeframe_minutes(tf: str) -> int:
    return {"1m":1,"3m":3,"5m":5,"15m":15,"30m":30,"1h":60,"2h":120,"4h":240,"1d":375,"1w":1875}.get(tf, 15)


def _normalize_binance_symbol(symbol: str) -> str:
    s = symbol.upper().replace("/", "").replace("-", "")
    if s.endswith(("USDT", "BUSD", "USDC", "BTC", "ETH")):
        return s
    if s in {"BTC", "ETH", "BNB", "SOL", "XRP", "ADA", "DOGE"}:
        return f"{s}USDT"
    return s


def _binance_interval(tf: str) -> Optional[str]:
    mapping = {
        "1m": "1m",
        "3m": "3m",
        "5m": "5m",
        "15m": "15m",
        "30m": "30m",
        "1h": "1h",
        "2h": "2h",
        "4h": "4h",
        "1d": "1d",
        "1w": "1w",
    }
    return mapping.get(tf)
