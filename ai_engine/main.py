"""
OmegaBot AI Engine — FastAPI service on port 8001.
Provides BUY/SELL/HOLD signals via XGBoost ensemble.
"""
from __future__ import annotations
import asyncio
import logging
import time
from contextlib import asynccontextmanager
from datetime import datetime
from typing import Any, Dict, List, Optional

import structlog
from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field, model_validator

from ai_engine.core.features   import build_features, get_feature_columns
from ai_engine.core.decision   import combine_predictions
from ai_engine.models.xgb_model import XGBoostPredictor

log = structlog.get_logger()

xgb  = XGBoostPredictor()
FCOLS = get_feature_columns()
_startup_time = time.time()
_predict_count = 0


@asynccontextmanager
async def lifespan(app: FastAPI):
    log.info("AI Engine: loading models…")
    loop = asyncio.get_event_loop()
    try:
        await loop.run_in_executor(None, xgb.load_or_train, FCOLS)
        log.info("AI Engine: models ready")
    except Exception as e:
        log.error(f"Model load failed: {e}")
    yield
    log.info("AI Engine: shutdown")


app = FastAPI(title="OmegaBot AI Engine", version="1.0.0", lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


class OHLCVBar(BaseModel):
    open: float; high: float; low: float; close: float; volume: float
    time: Optional[str] = None

    @model_validator(mode="before")
    @classmethod
    def _aliases(cls, data):
        if isinstance(data, dict):
            aliases = {"o":"open","h":"high","l":"low","c":"close","v":"volume","t":"time"}
            return {aliases.get(k, k): v for k, v in data.items()}
        return data


class PredictRequest(BaseModel):
    symbol:    str
    exchange:  str = "NSE"
    timeframe: str = "15m"
    data:      List[OHLCVBar] = Field(..., min_length=60)


class PredictResponse(BaseModel):
    symbol: str; signal: str; confidence: float; agreement: bool
    xgb_signal: str; xgb_confidence: float; combined_score: float
    reasoning: str; target_price: float; direction_pct: float; timestamp: str


@app.get("/health")
async def health():
    return {
        "status":          "ok",
        "service":         "omegabot-ai-engine",
        "xgb_ready":       xgb.is_ready,
        "uptime_seconds":  round(time.time() - _startup_time),
        "predictions_made":_predict_count,
        "timestamp":       datetime.utcnow().isoformat(),
    }


@app.get("/models")
async def model_info():
    return {"features": FCOLS, "n_features": len(FCOLS), "xgb_ready": xgb.is_ready}


@app.post("/predict", response_model=PredictResponse)
async def predict(req: PredictRequest):
    global _predict_count
    if not xgb.is_ready:
        raise HTTPException(503, "Models not ready — wait ~60s for training")

    try:
        ohlcv = [bar.model_dump() for bar in req.data]
        df = build_features(ohlcv)
        if len(df) < 35:
            raise HTTPException(422, f"Insufficient clean bars: {len(df)}")

        current_price = df["close"].iloc[-1]
        xgb_pred, xgb_conf = xgb.predict(df, FCOLS)
        result = combine_predictions(xgb_pred, xgb_conf, current_price)

        _predict_count += 1
        return PredictResponse(
            symbol=req.symbol,
            signal=result.signal,
            confidence=result.confidence,
            agreement=result.agreement,
            xgb_signal=result.xgb_signal,
            xgb_confidence=result.xgb_confidence,
            combined_score=result.combined_score,
            reasoning=result.reasoning,
            target_price=result.target_price,
            direction_pct=result.direction_pct,
            timestamp=datetime.utcnow().isoformat(),
        )
    except HTTPException:
        raise
    except Exception as e:
        log.error("predict_error", error=str(e))
        raise HTTPException(500, f"Prediction failed: {e}")


@app.post("/retrain")
async def retrain(symbol: str = "RELIANCE", background_tasks: BackgroundTasks = None):
    def _do():
        xgb.load_or_train(FCOLS, force=True)
    if background_tasks:
        background_tasks.add_task(_do)
    return {"status": "retraining_started", "symbol": symbol}


@app.get("/ping")
async def ping():
    return {"pong": True}
