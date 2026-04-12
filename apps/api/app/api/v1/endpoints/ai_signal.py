"""AI Signal endpoint — proxies to the ML engine service."""
from typing import Optional, List
from fastapi import APIRouter, Query
from pydantic import BaseModel

router = APIRouter()


class OHLCVItem(BaseModel):
    open: float; high: float; low: float; close: float; volume: float
    time: Optional[str] = None


class AISignalRequest(BaseModel):
    symbol: str; exchange: str = "NSE"; timeframe: str = "15m"
    data: Optional[List[OHLCVItem]] = None


@router.get("/health")
async def ai_health():
    from app.services.ai_engine_client import check_health
    return await check_health()


@router.post("/predict")
async def predict_signal(req: AISignalRequest):
    from app.services.ai_engine_client import get_ai_signal
    from app.adapters.marketdata.mock_data import MockMarketDataAdapter
    from datetime import datetime, timedelta

    if req.data:
        ohlcv = [d.model_dump() for d in req.data]
    else:
        adapter = MockMarketDataAdapter()
        await adapter.connect()
        bars = await adapter.get_historical_ohlcv(
            req.symbol, req.exchange, req.timeframe,
            datetime.utcnow() - timedelta(days=30), datetime.utcnow(),
        )
        ohlcv = [{"open": b.open, "high": b.high, "low": b.low,
                  "close": b.close, "volume": b.volume} for b in bars]

    result = await get_ai_signal(req.symbol, ohlcv, req.exchange, req.timeframe)
    if result is None:
        return {"symbol": req.symbol, "signal": "HOLD", "confidence": 0.0,
                "agreement": False, "available": False,
                "message": "AI Engine not running. Start: docker compose --profile ai up ai_engine"}
    return {**result, "available": True}


@router.get("/quick/{symbol}")
async def quick_signal(symbol: str, exchange: str = Query("NSE"), timeframe: str = Query("15m")):
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
            return {**result, "available": True}
    except Exception:
        pass
    return {"symbol": symbol, "signal": "HOLD", "confidence": 0.0, "available": False}
