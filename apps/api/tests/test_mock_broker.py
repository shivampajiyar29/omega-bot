"""Tests for Mock Broker Adapter."""
import asyncio
import pytest


@pytest.fixture
async def broker():
    from app.adapters.broker.mock_broker import MockBrokerAdapter
    b = MockBrokerAdapter(config={"initial_capital": 100_000, "fill_delay_ms": 0})
    await b.connect()
    b.update_price("RELIANCE", 2800.0)
    b.update_price("BTCUSDT", 87000.0)
    yield b
    await b.disconnect()


@pytest.mark.asyncio
async def test_connect(broker):
    assert broker.is_connected


@pytest.mark.asyncio
async def test_market_buy_fills(broker):
    order = await broker.place_order("RELIANCE", "buy", "market", 10)
    assert order.status == "filled"
    assert order.filled_quantity == 10
    assert order.avg_fill_price > 0


@pytest.mark.asyncio
async def test_cash_reduces_after_buy(broker):
    acc_before = await broker.get_account()
    await broker.place_order("RELIANCE", "buy", "market", 10)
    acc_after = await broker.get_account()
    assert acc_after["cash"] < acc_before["cash"]


@pytest.mark.asyncio
async def test_position_created_after_buy(broker):
    await broker.place_order("RELIANCE", "buy", "market", 5)
    pos = await broker.get_position("RELIANCE")
    assert pos is not None
    assert pos.quantity == 5


@pytest.mark.asyncio
async def test_sell_closes_position(broker):
    await broker.place_order("RELIANCE", "buy", "market", 5)
    await broker.place_order("RELIANCE", "sell", "market", 5)
    pos = await broker.get_position("RELIANCE")
    assert pos is None


@pytest.mark.asyncio
async def test_limit_order_stays_open(broker):
    order = await broker.place_order("RELIANCE", "buy", "limit", 5, price=1000.0)
    assert order.status == "open"


@pytest.mark.asyncio
async def test_cancel_order(broker):
    order = await broker.place_order("RELIANCE", "buy", "limit", 5, price=1000.0)
    result = await broker.cancel_order(order.id)
    assert result is True


@pytest.mark.asyncio
async def test_get_account(broker):
    acc = await broker.get_account()
    assert "cash" in acc
    assert acc["cash"] > 0


@pytest.mark.asyncio
async def test_pnl_updates_with_price(broker):
    await broker.place_order("RELIANCE", "buy", "market", 10)
    broker.update_price("RELIANCE", 3000.0)
    pos = await broker.get_position("RELIANCE")
    assert pos.current_price == 3000.0
    assert pos.unrealized_pnl > 0


@pytest.mark.asyncio
async def test_multiple_symbols(broker):
    await broker.place_order("RELIANCE", "buy", "market", 5)
    broker.update_price("BTCUSDT", 87000.0)
    await broker.place_order("BTCUSDT", "buy", "market", 1)
    positions = await broker.get_positions()
    symbols = [p.symbol for p in positions]
    assert "RELIANCE" in symbols
