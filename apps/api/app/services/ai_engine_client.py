"""
AI Engine client — calls the standalone ML service on port 8001.
All calls are non-blocking; failures return None gracefully.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

import httpx

log = logging.getLogger(__name__)
AI_ENGINE_URL = "http://localhost:8001"
_TIMEOUT = 8.0


async def get_ai_signal(symbol: str, ohlcv_data: List[Dict],
                         exchange: str = "NSE", timeframe: str = "15m") -> Optional[Dict]:
    if len(ohlcv_data) < 60:
        return None
    try:
        async with httpx.AsyncClient(timeout=_TIMEOUT) as c:
            r = await c.post(f"{AI_ENGINE_URL}/predict", json={
                "symbol": symbol, "exchange": exchange,
                "timeframe": timeframe, "data": ohlcv_data[-200:],
            })
            r.raise_for_status()
            return r.json()
    except httpx.ConnectError:
        log.debug("AI Engine offline — skipping signal")
    except Exception as e:
        log.warning(f"AI Engine error: {e}")
    return None


async def check_health() -> Dict:
    try:
        async with httpx.AsyncClient(timeout=3.0) as c:
            r = await c.get(f"{AI_ENGINE_URL}/health")
            return r.json()
    except Exception:
        return {"status": "unavailable", "xgb_ready": False}
