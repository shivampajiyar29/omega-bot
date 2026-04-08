"""
Database Models — OmegaBot Personal Trading Platform
Single-user optimized. All tables use UUID primary keys.
"""
import uuid
from datetime import datetime
from typing import Optional, Any
from sqlalchemy import (
    Column, String, Float, Integer, Boolean, DateTime, JSON,
    Text, ForeignKey, Enum as SAEnum, UniqueConstraint, Index
)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import DeclarativeBase, relationship
from sqlalchemy.sql import func
import enum


class Base(DeclarativeBase):
    pass


def gen_uuid():
    return str(uuid.uuid4())


# ─── Enums ────────────────────────────────────────────────────────────────────

class TradingMode(str, enum.Enum):
    PAPER = "paper"
    LIVE = "live"

class OrderSide(str, enum.Enum):
    BUY = "buy"
    SELL = "sell"

class OrderType(str, enum.Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"
    STOP_LIMIT = "stop_limit"

class OrderStatus(str, enum.Enum):
    PENDING = "pending"
    OPEN = "open"
    FILLED = "filled"
    PARTIALLY_FILLED = "partially_filled"
    CANCELLED = "cancelled"
    REJECTED = "rejected"

class BotStatus(str, enum.Enum):
    RUNNING = "running"
    PAUSED = "paused"
    STOPPED = "stopped"
    ERROR = "error"

class MarketType(str, enum.Enum):
    EQUITY = "equity"
    FUTURES = "futures"
    OPTIONS = "options"
    CRYPTO = "crypto"
    FOREX = "forex"
    COMMODITY = "commodity"

class ConnectorStatus(str, enum.Enum):
    CONNECTED = "connected"
    DISCONNECTED = "disconnected"
    ERROR = "error"
    TESTING = "testing"

class AlertLevel(str, enum.Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


# ─── Settings ─────────────────────────────────────────────────────────────────

class AppSetting(Base):
    """Global application settings — key/value store."""
    __tablename__ = "app_settings"

    key: str = Column(String(128), primary_key=True)
    value: Any = Column(JSON)
    description: str = Column(Text, nullable=True)
    updated_at: datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())


class EnabledModule(Base):
    """Feature/module toggle table."""
    __tablename__ = "enabled_modules"

    name: str = Column(String(64), primary_key=True)
    enabled: bool = Column(Boolean, default=True, nullable=False)
    config: Any = Column(JSON, nullable=True)  # Module-specific config
    description: str = Column(Text, nullable=True)
    updated_at: datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ─── Connectors ───────────────────────────────────────────────────────────────

class BrokerConnector(Base):
    """Pluggable broker integration configuration."""
    __tablename__ = "broker_connectors"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name: str = Column(String(64), nullable=False, unique=True)  # e.g. "zerodha", "mock"
    display_name: str = Column(String(128), nullable=False)
    adapter_class: str = Column(String(256), nullable=False)  # Python import path
    status: ConnectorStatus = Column(SAEnum(ConnectorStatus), default=ConnectorStatus.DISCONNECTED)
    config: Any = Column(JSON, nullable=True)  # Encrypted/masked config
    enabled: bool = Column(Boolean, default=False)
    is_default: bool = Column(Boolean, default=False)
    trading_mode: TradingMode = Column(SAEnum(TradingMode), default=TradingMode.PAPER)
    market_types: Any = Column(JSON, default=list)  # List of MarketType values
    created_at: datetime = Column(DateTime, server_default=func.now())
    updated_at: datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())

    bots = relationship("Bot", back_populates="connector")


class MarketDataConnector(Base):
    """Market data provider configuration."""
    __tablename__ = "market_data_connectors"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name: str = Column(String(64), nullable=False, unique=True)
    display_name: str = Column(String(128), nullable=False)
    adapter_class: str = Column(String(256), nullable=False)
    status: ConnectorStatus = Column(SAEnum(ConnectorStatus), default=ConnectorStatus.DISCONNECTED)
    config: Any = Column(JSON, nullable=True)
    enabled: bool = Column(Boolean, default=False)
    supported_markets: Any = Column(JSON, default=list)
    created_at: datetime = Column(DateTime, server_default=func.now())
    updated_at: datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())


# ─── Watchlist ────────────────────────────────────────────────────────────────

class Watchlist(Base):
    __tablename__ = "watchlists"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name: str = Column(String(128), nullable=False)
    is_default: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, server_default=func.now())

    symbols = relationship("WatchlistSymbol", back_populates="watchlist", cascade="all, delete")


class WatchlistSymbol(Base):
    __tablename__ = "watchlist_symbols"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    watchlist_id: str = Column(UUID(as_uuid=False), ForeignKey("watchlists.id"), nullable=False)
    symbol: str = Column(String(32), nullable=False)
    exchange: str = Column(String(16), nullable=False)
    market_type: MarketType = Column(SAEnum(MarketType), default=MarketType.EQUITY)
    added_at: datetime = Column(DateTime, server_default=func.now())

    watchlist = relationship("Watchlist", back_populates="symbols")
    __table_args__ = (UniqueConstraint("watchlist_id", "symbol", "exchange"),)


# ─── Strategy ─────────────────────────────────────────────────────────────────

class Strategy(Base):
    """Strategy definition using JSON DSL."""
    __tablename__ = "strategies"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name: str = Column(String(256), nullable=False)
    description: str = Column(Text, nullable=True)
    market_type: MarketType = Column(SAEnum(MarketType), default=MarketType.EQUITY)
    dsl: Any = Column(JSON, nullable=False)  # Strategy JSON DSL definition
    is_active: bool = Column(Boolean, default=True)
    tags: Any = Column(JSON, default=list)
    created_at: datetime = Column(DateTime, server_default=func.now())
    updated_at: datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())

    versions = relationship("StrategyVersion", back_populates="strategy", cascade="all, delete")
    bots = relationship("Bot", back_populates="strategy")
    backtests = relationship("Backtest", back_populates="strategy")


class StrategyVersion(Base):
    """Immutable snapshot of a strategy at a point in time."""
    __tablename__ = "strategy_versions"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    strategy_id: str = Column(UUID(as_uuid=False), ForeignKey("strategies.id"), nullable=False)
    version: int = Column(Integer, nullable=False)
    dsl_snapshot: Any = Column(JSON, nullable=False)
    change_notes: str = Column(Text, nullable=True)
    created_at: datetime = Column(DateTime, server_default=func.now())

    strategy = relationship("Strategy", back_populates="versions")
    __table_args__ = (UniqueConstraint("strategy_id", "version"),)


# ─── Bots ─────────────────────────────────────────────────────────────────────

class Bot(Base):
    """A running instance of a strategy."""
    __tablename__ = "bots"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name: str = Column(String(256), nullable=False)
    strategy_id: str = Column(UUID(as_uuid=False), ForeignKey("strategies.id"), nullable=False)
    connector_id: str = Column(UUID(as_uuid=False), ForeignKey("broker_connectors.id"), nullable=False)
    symbol: str = Column(String(32), nullable=False)
    exchange: str = Column(String(16), nullable=False)
    market_type: MarketType = Column(SAEnum(MarketType), default=MarketType.EQUITY)
    trading_mode: TradingMode = Column(SAEnum(TradingMode), default=TradingMode.PAPER)
    status: BotStatus = Column(SAEnum(BotStatus), default=BotStatus.STOPPED)
    config: Any = Column(JSON, nullable=True)  # Override params
    risk_config: Any = Column(JSON, nullable=True)  # Per-bot risk overrides
    started_at: Optional[datetime] = Column(DateTime, nullable=True)
    stopped_at: Optional[datetime] = Column(DateTime, nullable=True)
    created_at: datetime = Column(DateTime, server_default=func.now())
    updated_at: datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())

    strategy = relationship("Strategy", back_populates="bots")
    connector = relationship("BrokerConnector", back_populates="bots")
    orders = relationship("Order", back_populates="bot")


# ─── Orders & Fills ───────────────────────────────────────────────────────────

class Order(Base):
    __tablename__ = "orders"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    bot_id: Optional[str] = Column(UUID(as_uuid=False), ForeignKey("bots.id"), nullable=True)
    connector_id: str = Column(UUID(as_uuid=False), ForeignKey("broker_connectors.id"), nullable=False)
    broker_order_id: Optional[str] = Column(String(128), nullable=True)  # External broker ID
    symbol: str = Column(String(32), nullable=False)
    exchange: str = Column(String(16), nullable=False)
    market_type: MarketType = Column(SAEnum(MarketType), default=MarketType.EQUITY)
    side: OrderSide = Column(SAEnum(OrderSide), nullable=False)
    order_type: OrderType = Column(SAEnum(OrderType), nullable=False)
    quantity: float = Column(Float, nullable=False)
    price: Optional[float] = Column(Float, nullable=True)
    stop_price: Optional[float] = Column(Float, nullable=True)
    status: OrderStatus = Column(SAEnum(OrderStatus), default=OrderStatus.PENDING)
    filled_quantity: float = Column(Float, default=0.0)
    avg_fill_price: Optional[float] = Column(Float, nullable=True)
    trading_mode: TradingMode = Column(SAEnum(TradingMode), default=TradingMode.PAPER)
    tags: Any = Column(JSON, default=dict)
    placed_at: datetime = Column(DateTime, server_default=func.now())
    updated_at: datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())

    bot = relationship("Bot", back_populates="orders")
    fills = relationship("Fill", back_populates="order", cascade="all, delete")

    __table_args__ = (
        Index("ix_orders_symbol", "symbol"),
        Index("ix_orders_status", "status"),
        Index("ix_orders_placed_at", "placed_at"),
    )


class Fill(Base):
    """Individual execution/fill record."""
    __tablename__ = "fills"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    order_id: str = Column(UUID(as_uuid=False), ForeignKey("orders.id"), nullable=False)
    quantity: float = Column(Float, nullable=False)
    price: float = Column(Float, nullable=False)
    commission: float = Column(Float, default=0.0)
    filled_at: datetime = Column(DateTime, server_default=func.now())

    order = relationship("Order", back_populates="fills")


# ─── Positions ────────────────────────────────────────────────────────────────

class Position(Base):
    __tablename__ = "positions"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    symbol: str = Column(String(32), nullable=False)
    exchange: str = Column(String(16), nullable=False)
    market_type: MarketType = Column(SAEnum(MarketType), default=MarketType.EQUITY)
    side: OrderSide = Column(SAEnum(OrderSide), nullable=False)
    quantity: float = Column(Float, nullable=False)
    avg_price: float = Column(Float, nullable=False)
    current_price: Optional[float] = Column(Float, nullable=True)
    unrealized_pnl: Optional[float] = Column(Float, nullable=True)
    realized_pnl: float = Column(Float, default=0.0)
    is_open: bool = Column(Boolean, default=True)
    trading_mode: TradingMode = Column(SAEnum(TradingMode), default=TradingMode.PAPER)
    connector_id: str = Column(UUID(as_uuid=False), ForeignKey("broker_connectors.id"), nullable=False)
    opened_at: datetime = Column(DateTime, server_default=func.now())
    closed_at: Optional[datetime] = Column(DateTime, nullable=True)
    updated_at: datetime = Column(DateTime, server_default=func.now(), onupdate=func.now())

    __table_args__ = (
        Index("ix_positions_symbol_open", "symbol", "is_open"),
    )


# ─── Backtests ────────────────────────────────────────────────────────────────

class Backtest(Base):
    __tablename__ = "backtests"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    strategy_id: str = Column(UUID(as_uuid=False), ForeignKey("strategies.id"), nullable=False)
    name: str = Column(String(256), nullable=True)
    symbol: str = Column(String(32), nullable=False)
    exchange: str = Column(String(16), nullable=False)
    start_date: datetime = Column(DateTime, nullable=False)
    end_date: datetime = Column(DateTime, nullable=False)
    timeframe: str = Column(String(8), nullable=False)  # 1m, 5m, 15m, 1h, 1d, etc.
    initial_capital: float = Column(Float, nullable=False)
    commission_pct: float = Column(Float, default=0.0)
    slippage_pct: float = Column(Float, default=0.0)
    params: Any = Column(JSON, nullable=True)  # Strategy parameter overrides
    status: str = Column(String(16), default="pending")  # pending|running|completed|failed
    results: Any = Column(JSON, nullable=True)  # Summary metrics
    trade_log: Any = Column(JSON, nullable=True)  # Individual trades
    equity_curve: Any = Column(JSON, nullable=True)  # Time-series equity
    error_message: str = Column(Text, nullable=True)
    started_at: Optional[datetime] = Column(DateTime, nullable=True)
    completed_at: Optional[datetime] = Column(DateTime, nullable=True)
    created_at: datetime = Column(DateTime, server_default=func.now())

    strategy = relationship("Strategy", back_populates="backtests")


# ─── Portfolio ────────────────────────────────────────────────────────────────

class PortfolioSnapshot(Base):
    """Daily portfolio value snapshots."""
    __tablename__ = "portfolio_snapshots"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    date: datetime = Column(DateTime, nullable=False, index=True)
    total_value: float = Column(Float, nullable=False)
    cash: float = Column(Float, nullable=False)
    positions_value: float = Column(Float, nullable=False)
    daily_pnl: float = Column(Float, default=0.0)
    total_pnl: float = Column(Float, default=0.0)
    trading_mode: TradingMode = Column(SAEnum(TradingMode), default=TradingMode.PAPER)
    snapshot_data: Any = Column(JSON, nullable=True)


# ─── Risk ─────────────────────────────────────────────────────────────────────

class RiskProfile(Base):
    """Named risk configuration presets."""
    __tablename__ = "risk_profiles"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    name: str = Column(String(128), nullable=False, unique=True)
    max_daily_loss: float = Column(Float, nullable=False)
    max_trade_loss: float = Column(Float, nullable=False)
    max_open_positions: int = Column(Integer, nullable=False)
    max_order_value: float = Column(Float, nullable=False)
    max_margin_pct: float = Column(Float, default=80.0)
    allowed_hours_start: Optional[str] = Column(String(8), nullable=True)  # "09:15"
    allowed_hours_end: Optional[str] = Column(String(8), nullable=True)    # "15:30"
    symbol_blacklist: Any = Column(JSON, default=list)
    symbol_whitelist: Any = Column(JSON, default=list)
    is_active: bool = Column(Boolean, default=False)
    created_at: datetime = Column(DateTime, server_default=func.now())


class RiskEvent(Base):
    """Audit trail of risk-related events."""
    __tablename__ = "risk_events"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    event_type: str = Column(String(64), nullable=False)  # max_loss_hit, kill_switch, etc.
    severity: str = Column(String(16), default="warning")
    message: str = Column(Text, nullable=False)
    extra_metadata: Any = Column(JSON, nullable=True)
    occurred_at: datetime = Column(DateTime, server_default=func.now())

    __table_args__ = (Index("ix_risk_events_occurred_at", "occurred_at"),)


# ─── Alerts & Logs ────────────────────────────────────────────────────────────

class Alert(Base):
    __tablename__ = "alerts"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    title: str = Column(String(256), nullable=False)
    message: str = Column(Text, nullable=False)
    level: AlertLevel = Column(SAEnum(AlertLevel), default=AlertLevel.INFO)
    source: str = Column(String(64), nullable=True)  # bot_id, strategy_id, system
    is_read: bool = Column(Boolean, default=False)
    extra_metadata: Any = Column(JSON, nullable=True)
    created_at: datetime = Column(DateTime, server_default=func.now(), index=True)


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id: str = Column(UUID(as_uuid=False), primary_key=True, default=gen_uuid)
    action: str = Column(String(128), nullable=False)
    entity_type: str = Column(String(64), nullable=True)
    entity_id: str = Column(String(64), nullable=True)
    details: Any = Column(JSON, nullable=True)
    ip_address: str = Column(String(45), nullable=True)
    logged_at: datetime = Column(DateTime, server_default=func.now(), index=True)
