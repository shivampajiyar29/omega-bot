"""
Paper trading: instant fills against latest Redis prices using existing Order / Position models.
"""
from __future__ import annotations

import json
import logging
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.core.database import AsyncSessionLocal
from app.models.models import (
    ConnectorStatus,
    Fill,
    MarketType,
    Order,
    OrderSide,
    OrderStatus,
    OrderType,
    Position,
    TradingMode,
    BrokerConnector,
)
from app.services import market_stream

logger = logging.getLogger(__name__)

SIGNAL_KEY = "omegabot:paper:signal:{symbol}"
LAST_ACTION_KEY = "omegabot:paper:last_action:{symbol}"
LOCK_KEY = "omegabot:paper:lock:{symbol}"

DEFAULT_EXCHANGE = "MOCK"
DEFAULT_QTY = 1.0


def _redis() -> redis.Redis:
    return redis.from_url(settings.REDIS_URL, decode_responses=True)


def _market_type(symbol: str) -> MarketType:
    s = symbol.upper()
    if "BTC" in s or "ETH" in s or s.endswith("USDT"):
        return MarketType.CRYPTO
    return MarketType.EQUITY


async def ensure_paper_connector(session: AsyncSession) -> str:
    """Return default paper broker id, creating a mock connector if missing."""
    result = await session.execute(
        select(BrokerConnector).where(BrokerConnector.is_default.is_(True)).limit(1)
    )
    row = result.scalar_one_or_none()
    if row:
        return row.id

    result2 = await session.execute(
        select(BrokerConnector).where(BrokerConnector.name == "mock").limit(1)
    )
    row2 = result2.scalar_one_or_none()
    if row2:
        return row2.id

    c = BrokerConnector(
        id=str(uuid.uuid4()),
        name="mock",
        display_name="Mock Paper",
        adapter_class="app.adapters.broker.mock_broker.MockBrokerAdapter",
        enabled=True,
        is_default=True,
        status=ConnectorStatus.CONNECTED,
        trading_mode=TradingMode.PAPER,
    )
    session.add(c)
    await session.flush()
    return c.id


async def create_order(
    session: AsyncSession,
    connector_id: str,
    symbol: str,
    side: str,
    qty: float,
    price: float,
    *,
    bot_id: Optional[str] = None,
) -> Order:
    """Create a pending paper order."""
    side_e = OrderSide.BUY if side.lower() == "buy" else OrderSide.SELL
    o = Order(
        id=str(uuid.uuid4()),
        bot_id=bot_id,
        connector_id=connector_id,
        broker_order_id=None,
        symbol=symbol.upper(),
        exchange=DEFAULT_EXCHANGE,
        market_type=_market_type(symbol),
        side=side_e,
        order_type=OrderType.MARKET,
        quantity=qty,
        price=price,
        status=OrderStatus.PENDING,
        filled_quantity=0.0,
        trading_mode=TradingMode.PAPER,
        tags={"source": "paper_ai", "automated": True},
    )
    session.add(o)
    await session.flush()
    return o


async def execute_order(session: AsyncSession, order_id: str) -> Optional[Order]:
    """Instant full fill at order.price; updates fills, order, positions."""
    o = await session.get(Order, order_id)
    if not o:
        return None
    if o.status not in (OrderStatus.PENDING, OrderStatus.OPEN, OrderStatus.PARTIALLY_FILLED):
        return o

    fill_price = float(o.price or 0.0)
    if fill_price <= 0:
        tick = market_stream.get_latest_price(o.symbol)
        fill_price = float(tick["price"]) if tick else 0.0
    if fill_price <= 0:
        logger.warning("execute_order: no price for %s", o.symbol)
        return o

    qty = float(o.quantity)
    if o.side == OrderSide.SELL:
        res = await session.execute(
            select(Position).where(
                Position.symbol == o.symbol,
                Position.exchange == o.exchange,
                Position.connector_id == o.connector_id,
                Position.is_open.is_(True),
                Position.side == OrderSide.BUY,
                Position.trading_mode == o.trading_mode,
            )
        )
        pos_chk = res.scalar_one_or_none()
        if pos_chk is None or pos_chk.quantity + 1e-9 < qty:
            o.status = OrderStatus.REJECTED
            await session.flush()
            return o
    fill = Fill(
        id=str(uuid.uuid4()),
        order_id=o.id,
        quantity=qty,
        price=fill_price,
        commission=0.0,
        filled_at=datetime.now(timezone.utc),
    )
    session.add(fill)

    o.status = OrderStatus.FILLED
    o.filled_quantity = qty
    o.avg_fill_price = fill_price
    o.broker_order_id = f"paper-{o.id[:8]}"

    await _apply_fill_to_positions(session, o, fill_price, qty)
    await session.flush()
    return o


async def _apply_fill_to_positions(session: AsyncSession, o: Order, price: float, qty: float) -> None:
    mt = o.market_type
    mode = o.trading_mode

    if o.side == OrderSide.BUY:
        q = select(Position).where(
            Position.symbol == o.symbol,
            Position.exchange == o.exchange,
            Position.connector_id == o.connector_id,
            Position.is_open.is_(True),
            Position.side == OrderSide.BUY,
            Position.trading_mode == mode,
        )
        res = await session.execute(q)
        pos = res.scalar_one_or_none()
        if pos is None:
            pos = Position(
                id=str(uuid.uuid4()),
                symbol=o.symbol,
                exchange=o.exchange,
                market_type=mt,
                side=OrderSide.BUY,
                quantity=qty,
                avg_price=price,
                current_price=price,
                unrealized_pnl=0.0,
                realized_pnl=0.0,
                is_open=True,
                trading_mode=mode,
                connector_id=o.connector_id,
            )
            session.add(pos)
        else:
            nq = pos.quantity + qty
            pos.avg_price = (pos.quantity * pos.avg_price + qty * price) / nq if nq else price
            pos.quantity = nq
            pos.current_price = price
            pos.unrealized_pnl = (pos.current_price - pos.avg_price) * pos.quantity
    else:
        q = select(Position).where(
            Position.symbol == o.symbol,
            Position.exchange == o.exchange,
            Position.connector_id == o.connector_id,
            Position.is_open.is_(True),
            Position.side == OrderSide.BUY,
            Position.trading_mode == mode,
        )
        res = await session.execute(q)
        pos = res.scalar_one_or_none()
        if pos is None or pos.quantity <= 0:
            logger.warning("SELL with no long position for %s", o.symbol)
            return

        close_qty = min(qty, pos.quantity)
        pnl = (price - pos.avg_price) * close_qty
        pos.realized_pnl = float(pos.realized_pnl or 0.0) + pnl
        pos.quantity -= close_qty
        pos.current_price = price
        if pos.quantity <= 1e-9:
            pos.quantity = 0.0
            pos.is_open = False
            pos.closed_at = datetime.now(timezone.utc)
        else:
            pos.unrealized_pnl = (pos.current_price - pos.avg_price) * pos.quantity


async def update_positions(session: AsyncSession) -> None:
    """Mark-to-market open positions using Redis latest prices."""
    result = await session.execute(select(Position).where(Position.is_open.is_(True)))
    for pos in result.scalars().all():
        tick = market_stream.get_latest_price(pos.symbol)
        if not tick:
            continue
        cur = float(tick["price"])
        pos.current_price = cur
        if pos.side == OrderSide.BUY:
            pos.unrealized_pnl = (cur - pos.avg_price) * pos.quantity


async def update_balance() -> None:
    """Reserved: portfolio summary derives cash from positions in existing API."""
    return None


async def execute_pending_signals_async() -> None:
    """
    Read AI signals from Redis; on action change, place paper trades.
    Avoids re-trading the same signal repeatedly.
    """
    r = _redis()

    for sym in market_stream.DEFAULT_SYMBOLS:
        raw_sig = r.get(SIGNAL_KEY.format(symbol=sym))
        if not raw_sig:
            continue
        try:
            sig: Dict[str, Any] = json.loads(raw_sig)
        except json.JSONDecodeError:
            continue

        action = str(sig.get("action", "hold")).lower()
        prev = r.get(LAST_ACTION_KEY.format(symbol=sym))
        if prev == action:
            continue

        if action == "hold":
            r.set(LAST_ACTION_KEY.format(symbol=sym), "hold")
            continue

        if not r.set(LOCK_KEY.format(symbol=sym), "1", nx=True, ex=5):
            continue

        try:
            tick = market_stream.get_latest_price(sym)
            price = float(tick["price"]) if tick else 0.0
            if price <= 0:
                continue

            async with AsyncSessionLocal() as session:
                cid = await ensure_paper_connector(session)

                if action == "buy":
                    o = await create_order(
                        session, cid, sym, "buy", DEFAULT_QTY, price
                    )
                else:
                    res = await session.execute(
                        select(Position).where(
                            Position.symbol == sym,
                            Position.is_open.is_(True),
                            Position.side == OrderSide.BUY,
                            Position.trading_mode == TradingMode.PAPER,
                        )
                    )
                    p = res.scalar_one_or_none()
                    sell_qty = DEFAULT_QTY
                    if p is not None:
                        sell_qty = min(DEFAULT_QTY, float(p.quantity))
                    if sell_qty <= 0:
                        r.set(LAST_ACTION_KEY.format(symbol=sym), action)
                        continue
                    o = await create_order(
                        session, cid, sym, "sell", sell_qty, price
                    )

                await execute_order(session, o.id)
                await update_positions(session)
                await session.commit()

            r.set(LAST_ACTION_KEY.format(symbol=sym), action)
            logger.info("paper trade executed %s %s @ %s", sym, action, price)
        except Exception:
            logger.exception("execute_pending_signals failed for %s", sym)
        finally:
            r.delete(LOCK_KEY.format(symbol=sym))
