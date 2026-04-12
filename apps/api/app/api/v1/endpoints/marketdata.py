"""
Market Data API — OHLCV, quotes, indices.
Tries Binance REST first; falls back to mock data generator on any failure.
This ensures the API never crashes due to network unavailability.
"""
from typing import List, Optional
from datetime import datetime, timedelta, timezone
import logging

from fastapi import APIRouter, Query

router = APIRouter()
log = logging.getLogger(__name__)

BINANCE_REST = "https://api.binance.com/api/v3"

# ─── Binance helpers ──────────────────────────────────────────────────────────

def _tf_to_binance(tf: str) -> Optional[str]:
    return {"1m":"1m","3m":"3m","5m":"5m","15m":"15m","30m":"30m",
            "1h":"1h","2h":"2h","4h":"4h","1d":"1d","1w":"1w"}.get(tf)


def _tf_minutes(tf: str) -> int:
    return {"1m":1,"3m":3,"5m":5,"15m":15,"30m":30,"1h":60,"2h":120,
            "4h":240,"1d":375,"1w":1875}.get(tf, 15)


def _to_binance_symbol(symbol: str) -> str:
    s = symbol.upper().replace("/","").replace("-","")
    if s.endswith(("USDT","BUSD","USDC","BTC","ETH")):
        return s
    if s in {"BTC","ETH","BNB","SOL","XRP","ADA","DOGE"}:
        return f"{s}USDT"
    return s


async def _try_binance(path: str, params: dict) -> Optional[dict]:
    """Try Binance REST; return None on any error."""
    try:
        import aiohttp
        async with aiohttp.ClientSession(timeout=aiohttp.ClientTimeout(total=8)) as s:
            async with s.get(f"{BINANCE_REST}{path}", params=params) as r:
                if r.status < 400:
                    return await r.json()
    except Exception as e:
        log.debug(f"Binance unavailable ({path}): {e}")
    return None


# ─── Mock fallback helpers ────────────────────────────────────────────────────

async def _mock_ohlcv(symbol: str, exchange: str, timeframe: str, limit: int) -> List[dict]:
    from app.adapters.marketdata.mock_data import MockMarketDataAdapter
    adapter = MockMarketDataAdapter()
    await adapter.connect()
    bars = await adapter.get_historical_ohlcv(
        symbol, exchange, timeframe,
        datetime.utcnow() - timedelta(minutes=_tf_minutes(timeframe) * limit),
        datetime.utcnow(),
    )
    return [{"t": b.timestamp.isoformat(), "o": b.open, "h": b.high,
             "l": b.low, "c": b.close, "v": b.volume} for b in bars[-limit:]]


MOCK_INDICES = [
    {"symbol": "BTCUSDT",  "name": "Bitcoin",  "price": 87432.0, "change": 1975.5, "change_pct": 2.31},
    {"symbol": "ETHUSDT",  "name": "Ethereum", "price": 3221.4,  "change": 59.2,   "change_pct": 1.87},
    {"symbol": "BNBUSDT",  "name": "BNB",      "price": 612.3,   "change": 8.1,    "change_pct": 1.34},
    {"symbol": "SOLUSDT",  "name": "Solana",   "price": 183.5,   "change": -2.1,   "change_pct": -1.13},
    {"symbol": "XRPUSDT",  "name": "XRP",      "price": 0.624,   "change": 0.012,  "change_pct": 1.96},
    {"symbol": "NIFTY50",  "name": "Nifty 50", "price": 24832.15,"change": 182.35, "change_pct": 0.74},
    {"symbol": "SENSEX",   "name": "Sensex",   "price": 81547.89,"change": 501.23, "change_pct": 0.62},
]


# ─── Endpoints ────────────────────────────────────────────────────────────────

@router.get("/search", response_model=List[dict])
async def search_instruments(
    q: str = Query(..., min_length=1),
    market_type: str = "equity",
):
    """Search instruments. Uses Binance if available, else returns mock NSE/crypto list."""
    data = await _try_binance("/exchangeInfo", {})
    if data:
        q_up = q.upper()
        out = []
        for item in data.get("symbols", []):
            sym = item.get("symbol", "")
            if q_up in sym:
                out.append({"symbol": sym, "name": sym,
                            "exchange": "BINANCE", "type": "crypto"})
            if len(out) >= 50:
                break
        if out:
            return out

    # Fallback: static NSE list
    NSE_SYMBOLS = ["RELIANCE","TCS","INFY","HDFC","BAJFINANCE","WIPRO",
                   "HCLTECH","AXISBANK","ICICIBANK","SBIN","TATAMOTORS",
                   "MARUTI","NIFTY50","BANKNIFTY"]
    q_up = q.upper()
    return [{"symbol": s, "name": s, "exchange": "NSE", "type": "equity"}
            for s in NSE_SYMBOLS if q_up in s][:20]


@router.get("/ohlcv", response_model=List[dict])
async def get_ohlcv(
    symbol: str,
    exchange: str = "NSE",
    timeframe: str = "15m",
    from_date: Optional[str] = None,
    to_date: Optional[str] = None,
    limit: int = 200,
):
    """Fetch OHLCV. Uses Binance for crypto symbols, mock data for others."""
    interval = _tf_to_binance(timeframe)
    end = datetime.fromisoformat(to_date) if to_date else datetime.now(timezone.utc)
    start = (datetime.fromisoformat(from_date) if from_date
             else end - timedelta(minutes=_tf_minutes(timeframe) * limit))

    # Try Binance for crypto (USDT pairs)
    bsym = _to_binance_symbol(symbol)
    if interval and (exchange.upper() in ("BINANCE","CRYPTO") or "USDT" in bsym.upper()):
        data = await _try_binance("/klines", {
            "symbol": bsym, "interval": interval,
            "startTime": int(start.timestamp() * 1000),
            "endTime":   int(end.timestamp() * 1000),
            "limit":     min(limit, 1000),
        })
        if data and isinstance(data, list):
            return [{
                "t": datetime.fromtimestamp(k[0]/1000, tz=timezone.utc).isoformat(),
                "o": float(k[1]), "h": float(k[2]),
                "l": float(k[3]), "c": float(k[4]), "v": float(k[5]),
            } for k in data][-limit:]

    # Fallback to mock generator
    return await _mock_ohlcv(symbol, exchange, timeframe, limit)


@router.get("/quote/{symbol}", response_model=dict)
async def get_quote(symbol: str, exchange: str = "NSE"):
    """Live quote — Binance for crypto, mock for others."""
    bsym = _to_binance_symbol(symbol)
    if exchange.upper() in ("BINANCE","CRYPTO") or "USDT" in bsym.upper():
        data = await _try_binance("/ticker/price", {"symbol": bsym})
        if data:
            return {"symbol": symbol, "exchange": "BINANCE",
                    "price": float(data.get("price", 0)),
                    "timestamp": datetime.now(timezone.utc).isoformat()}

    # Mock fallback
    from app.services.market_stream import get_price_from_redis
    price = get_price_from_redis(symbol) or 2800.0
    return {"symbol": symbol, "exchange": exchange, "price": price,
            "timestamp": datetime.utcnow().isoformat()}


@router.get("/indices", response_model=List[dict])
async def get_indices():
    """Major indices/crypto. Binance live if available, mock otherwise."""
    pairs = ["BTCUSDT","ETHUSDT","BNBUSDT","SOLUSDT","XRPUSDT"]
    data = await _try_binance("/ticker/24hr", {})
    if data and isinstance(data, list):
        by_sym = {x.get("symbol"): x for x in data if x.get("symbol") in pairs}
        result = []
        for p in pairs:
            d = by_sym.get(p)
            if d:
                result.append({
                    "symbol": p, "name": p,
                    "price": float(d.get("lastPrice", 0)),
                    "change": float(d.get("priceChange", 0)),
                    "change_pct": float(d.get("priceChangePercent", 0)),
                })
        if result:
            return result

    return MOCK_INDICES


@router.get("/timeframes", response_model=List[dict])
async def get_supported_timeframes():
    return [
        {"value":"1m","label":"1 Minute"},{"value":"3m","label":"3 Minutes"},
        {"value":"5m","label":"5 Minutes"},{"value":"15m","label":"15 Minutes"},
        {"value":"30m","label":"30 Minutes"},{"value":"1h","label":"1 Hour"},
        {"value":"2h","label":"2 Hours"},{"value":"4h","label":"4 Hours"},
        {"value":"1d","label":"Daily"},{"value":"1w","label":"Weekly"},
    ]
