"""
Custom Indicators API
Lets users create, test, and manage their own Python indicators.
"""
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import uuid

from app.strategy.custom_indicators import (
    CustomIndicator,
    register_indicator,
    get_indicator,
    list_indicators,
    validate_indicator_code,
    execute_custom_indicator,
    IndicatorSafetyError,
)

router = APIRouter()


class IndicatorCreate(BaseModel):
    name:          str
    description:   str = ""
    code:          str
    params_schema: Dict[str, Any] = {}
    output_type:   str = "line"   # line | histogram | signal
    color:         str = "#4a9eff"


class IndicatorTest(BaseModel):
    code:   str
    params: Dict[str, Any] = {}
    bars:   int = 50     # number of synthetic bars to test against


class AIGenerateRequest(BaseModel):
    description: str
    params:      Optional[Dict[str, Any]] = None


# ─── List & Get ───────────────────────────────────────────────────────────────

@router.get("/", response_model=List[dict])
async def list_custom_indicators():
    """List all custom indicators (built-ins + user-created)."""
    return list_indicators()


@router.get("/{indicator_id}", response_model=dict)
async def get_custom_indicator(indicator_id: str):
    ind = get_indicator(indicator_id)
    if not ind:
        raise HTTPException(status_code=404, detail=f"Indicator '{indicator_id}' not found")
    return ind.to_dict()


# ─── Create ───────────────────────────────────────────────────────────────────

@router.post("/", response_model=dict, status_code=201)
async def create_custom_indicator(data: IndicatorCreate):
    """
    Create a new custom indicator from Python code.
    Code must define: def compute(df: pd.DataFrame, **params) -> pd.Series
    """
    # Safety validation
    try:
        validate_indicator_code(data.code)
    except IndicatorSafetyError as e:
        raise HTTPException(status_code=422, detail=f"Code validation failed: {e}")

    ind_id = str(uuid.uuid4())[:8]
    indicator = CustomIndicator(
        id=ind_id,
        name=data.name,
        description=data.description,
        code=data.code,
        params_schema=data.params_schema,
        output_type=data.output_type,
        color=data.color,
    )
    register_indicator(indicator)

    # TODO: persist to MongoDB
    # await mongo_db.indicators.insert_one(indicator.to_dict())

    return {**indicator.to_dict(), "message": "Indicator created and registered"}


# ─── Test ─────────────────────────────────────────────────────────────────────

@router.post("/test", response_model=dict)
async def test_indicator_code(data: IndicatorTest):
    """
    Run an indicator against synthetic data and return the output.
    Use this to verify your indicator before saving.
    """
    # Validate first
    try:
        validate_indicator_code(data.code)
    except IndicatorSafetyError as e:
        return {"valid": False, "error": str(e), "output": None}

    # Generate synthetic OHLCV data
    import pandas as pd
    import numpy as np

    n = data.bars
    rng = np.random.default_rng(42)
    prices = 1000 * np.cumprod(1 + rng.normal(0.0005, 0.012, n))

    df = pd.DataFrame({
        "open":   prices * (1 - rng.uniform(0, 0.005, n)),
        "high":   prices * (1 + rng.uniform(0, 0.008, n)),
        "low":    prices * (1 - rng.uniform(0, 0.008, n)),
        "close":  prices,
        "volume": rng.integers(100_000, 1_000_000, n).astype(float),
    })

    try:
        result = execute_custom_indicator(data.code, df, data.params)
        output_values = result.dropna().tail(20).tolist()
        return {
            "valid":       True,
            "output":      [round(v, 4) for v in output_values],
            "length":      len(result),
            "non_null":    result.notna().sum(),
            "min":         round(float(result.min()), 4),
            "max":         round(float(result.max()), 4),
            "last":        round(float(result.dropna().iloc[-1]), 4) if result.notna().any() else None,
            "error":       None,
        }
    except IndicatorSafetyError as e:
        return {"valid": False, "error": str(e), "output": None}
    except Exception as e:
        return {"valid": False, "error": f"Runtime error: {e}", "output": None}


# ─── AI Generation ────────────────────────────────────────────────────────────

@router.post("/generate", response_model=dict)
async def generate_indicator_with_ai(data: AIGenerateRequest):
    """
    Use AI to generate indicator Python code from a description.
    Requires an AI provider key in .env (GEMINI_API_KEY recommended).
    """
    try:
        from app.ai_assistant.provider import generate_custom_indicator_code
        result = await generate_custom_indicator_code(data.description, data.params)
        code = result["code"]

        # Validate generated code
        try:
            validate_indicator_code(code)
            valid = True
            error = None
        except IndicatorSafetyError as e:
            valid = False
            error = str(e)

        return {
            "code":     code,
            "valid":    valid,
            "error":    error,
            "provider": result.get("provider", "unknown"),
            "message":  "Review the code, then POST to /indicators to save it.",
        }
    except Exception as e:
        raise HTTPException(status_code=503, detail=f"AI generation failed: {e}")


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.delete("/{indicator_id}", response_model=dict)
async def delete_indicator(indicator_id: str):
    from app.strategy.custom_indicators import _INDICATOR_REGISTRY
    # Cannot delete built-ins
    builtins = {"hull_ma", "chandelier_exit", "squeeze_momentum", "wavetrend"}
    if indicator_id in builtins:
        raise HTTPException(status_code=400, detail="Cannot delete built-in indicators")
    if indicator_id in _INDICATOR_REGISTRY:
        del _INDICATOR_REGISTRY[indicator_id]
        # TODO: remove from MongoDB
        return {"deleted": True}
    raise HTTPException(status_code=404, detail="Indicator not found")


# ─── Use in backtest ──────────────────────────────────────────────────────────

@router.post("/{indicator_id}/compute", response_model=dict)
async def compute_indicator_on_data(
    indicator_id: str,
    symbol: str = "RELIANCE",
    exchange: str = "NSE",
    timeframe: str = "15m",
    params: Optional[Dict[str, Any]] = None,
):
    """
    Run a custom indicator on live/historical data and return values.
    Used by the chart UI to overlay custom indicators.
    """
    ind = get_indicator(indicator_id)
    if not ind:
        raise HTTPException(status_code=404, detail="Indicator not found")

    # Fetch data
    from datetime import datetime, timedelta
    from app.adapters.marketdata.mock_data import MockMarketDataAdapter
    import pandas as pd

    adapter = MockMarketDataAdapter()
    await adapter.connect()
    bars = await adapter.get_historical_ohlcv(
        symbol, exchange, timeframe,
        datetime.utcnow() - timedelta(days=30),
        datetime.utcnow(),
    )

    if not bars:
        raise HTTPException(status_code=404, detail="No price data available")

    df = pd.DataFrame([{
        "open": b.open, "high": b.high, "low": b.low,
        "close": b.close, "volume": b.volume,
    } for b in bars])

    try:
        result = execute_custom_indicator(ind.code, df, params or {})
        return {
            "indicator_id": indicator_id,
            "name":         ind.name,
            "output_type":  ind.output_type,
            "color":        ind.color,
            "values":       [
                {"time": bars[i].timestamp.isoformat(), "value": round(float(v), 4)}
                for i, v in enumerate(result)
                if not (v != v)  # filter NaN
            ],
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Indicator compute error: {e}")
