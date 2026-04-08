"""
Pydantic v2 schemas for request/response validation.
These are separate from SQLAlchemy models to keep the API contract clean.
"""
from __future__ import annotations
from typing import Any, Dict, List, Optional
from datetime import datetime
from pydantic import BaseModel, Field, field_validator
from enum import Enum


# ─── Enums ────────────────────────────────────────────────────────────────────

class TradingModeEnum(str, Enum):
    PAPER = "paper"
    LIVE  = "live"

class MarketTypeEnum(str, Enum):
    EQUITY    = "equity"
    FUTURES   = "futures"
    OPTIONS   = "options"
    CRYPTO    = "crypto"
    FOREX     = "forex"
    COMMODITY = "commodity"

class OrderSideEnum(str, Enum):
    BUY  = "buy"
    SELL = "sell"

class OrderTypeEnum(str, Enum):
    MARKET     = "market"
    LIMIT      = "limit"
    STOP       = "stop"
    STOP_LIMIT = "stop_limit"

class BotStatusEnum(str, Enum):
    RUNNING = "running"
    PAUSED  = "paused"
    STOPPED = "stopped"
    ERROR   = "error"


# ─── Strategy schemas ─────────────────────────────────────────────────────────

class StrategyCreateSchema(BaseModel):
    name:        str           = Field(..., min_length=1, max_length=256)
    description: Optional[str] = None
    market_type: MarketTypeEnum = MarketTypeEnum.EQUITY
    dsl:         Dict[str, Any] = Field(..., description="Strategy DSL JSON")
    tags:        List[str]     = Field(default_factory=list)

    @field_validator("dsl")
    @classmethod
    def validate_dsl(cls, v):
        from app.strategy.dsl import StrategyDSL
        try:
            StrategyDSL(**v)
        except Exception as e:
            raise ValueError(f"Invalid strategy DSL: {e}")
        return v


class StrategyUpdateSchema(BaseModel):
    name:        Optional[str]            = None
    description: Optional[str]            = None
    dsl:         Optional[Dict[str, Any]] = None
    is_active:   Optional[bool]           = None
    tags:        Optional[List[str]]      = None

    @field_validator("dsl")
    @classmethod
    def validate_dsl(cls, v):
        if v is None:
            return v
        from app.strategy.dsl import StrategyDSL
        try:
            StrategyDSL(**v)
        except Exception as e:
            raise ValueError(f"Invalid strategy DSL: {e}")
        return v


class StrategyResponseSchema(BaseModel):
    id:          str
    name:        str
    description: Optional[str]
    market_type: str
    dsl:         Dict[str, Any]
    is_active:   bool
    tags:        List[str]
    created_at:  str
    updated_at:  str

    class Config:
        from_attributes = True


# ─── Bot schemas ──────────────────────────────────────────────────────────────

class BotCreateSchema(BaseModel):
    name:         str               = Field(..., min_length=1)
    strategy_id:  str
    connector_id: str
    symbol:       str               = Field(..., min_length=1, max_length=32)
    exchange:     str               = Field(..., min_length=1, max_length=16)
    market_type:  MarketTypeEnum    = MarketTypeEnum.EQUITY
    trading_mode: TradingModeEnum   = TradingModeEnum.PAPER
    config:       Optional[Dict[str, Any]] = None
    risk_config:  Optional[Dict[str, Any]] = None

    @field_validator("symbol")
    @classmethod
    def uppercase_symbol(cls, v):
        return v.upper()

    @field_validator("exchange")
    @classmethod
    def uppercase_exchange(cls, v):
        return v.upper()


class BotUpdateSchema(BaseModel):
    name:         Optional[str]                   = None
    config:       Optional[Dict[str, Any]]         = None
    risk_config:  Optional[Dict[str, Any]]         = None
    trading_mode: Optional[TradingModeEnum]        = None


class BotResponseSchema(BaseModel):
    id:           str
    name:         str
    strategy_id:  str
    connector_id: str
    symbol:       str
    exchange:     str
    market_type:  str
    trading_mode: str
    status:       str
    config:       Optional[Dict[str, Any]]
    risk_config:  Optional[Dict[str, Any]]
    started_at:   Optional[str]
    stopped_at:   Optional[str]
    created_at:   str

    class Config:
        from_attributes = True


# ─── Order schemas ────────────────────────────────────────────────────────────

class OrderPlaceSchema(BaseModel):
    symbol:      str           = Field(..., min_length=1)
    exchange:    str           = "NSE"
    side:        OrderSideEnum
    order_type:  OrderTypeEnum = OrderTypeEnum.MARKET
    quantity:    float         = Field(gt=0)
    price:       Optional[float] = Field(None, gt=0)
    stop_price:  Optional[float] = Field(None, gt=0)
    bot_id:      Optional[str]   = None
    tags:        Optional[Dict[str, Any]] = None

    @field_validator("symbol")
    @classmethod
    def uppercase(cls, v):
        return v.upper()

    @field_validator("price", "stop_price")
    @classmethod
    def validate_price(cls, v, info):
        if v is not None and v <= 0:
            raise ValueError("Price must be positive")
        return v


class OrderResponseSchema(BaseModel):
    id:               str
    symbol:           str
    exchange:         str
    side:             str
    order_type:       str
    quantity:         float
    price:            Optional[float]
    status:           str
    filled_quantity:  float
    avg_fill_price:   Optional[float]
    trading_mode:     str
    placed_at:        str

    class Config:
        from_attributes = True


# ─── Backtest schemas ─────────────────────────────────────────────────────────

class BacktestCreateSchema(BaseModel):
    strategy_id:     str
    symbol:          str           = Field(..., min_length=1)
    exchange:        str           = "NSE"
    timeframe:       str           = "15m"
    start_date:      str           = Field(..., description="ISO date: 2024-01-01")
    end_date:        str           = Field(..., description="ISO date: 2024-12-31")
    initial_capital: float         = Field(100_000.0, gt=0)
    commission_pct:  float         = Field(0.03, ge=0, le=5.0)
    slippage_pct:    float         = Field(0.01, ge=0, le=5.0)
    params:          Optional[Dict[str, Any]] = None
    name:            Optional[str] = None

    @field_validator("start_date", "end_date")
    @classmethod
    def validate_date(cls, v):
        try:
            datetime.fromisoformat(v)
        except ValueError:
            raise ValueError(f"Invalid date format: {v}. Use ISO format: YYYY-MM-DD")
        return v

    @field_validator("end_date")
    @classmethod
    def end_after_start(cls, v, info):
        if "start_date" in info.data:
            start = datetime.fromisoformat(info.data["start_date"])
            end   = datetime.fromisoformat(v)
            if end <= start:
                raise ValueError("end_date must be after start_date")
        return v


# ─── Risk schemas ─────────────────────────────────────────────────────────────

class RiskProfileCreateSchema(BaseModel):
    name:                str
    max_daily_loss:      float  = Field(gt=0)
    max_trade_loss:      float  = Field(gt=0)
    max_open_positions:  int    = Field(gt=0, le=100)
    max_order_value:     float  = Field(gt=0)
    max_margin_pct:      float  = Field(default=80.0, ge=0, le=100)
    allowed_hours_start: Optional[str] = "09:15"
    allowed_hours_end:   Optional[str] = "15:30"
    symbol_blacklist:    List[str] = Field(default_factory=list)
    symbol_whitelist:    List[str] = Field(default_factory=list)


# ─── Webhook schemas ──────────────────────────────────────────────────────────

class TradingViewSignalSchema(BaseModel):
    symbol:   str
    action:   str = Field(..., pattern="^(buy|sell|long|short|exit|close_all)$")
    price:    Optional[float] = None
    quantity: Optional[float] = None
    exchange: str = "NSE"
    strategy: Optional[str]  = None
    comment:  Optional[str]  = None
    secret:   Optional[str]  = None
