"""Tests for Execution Engine and Bot Manager."""
import pytest


@pytest.mark.asyncio
async def test_execution_engine_start_stop():
    from app.execution.engine import ExecutionEngine
    engine = ExecutionEngine(broker_name="mock")
    await engine.start()
    assert engine.is_connected
    await engine.stop()
    assert not engine.is_connected


@pytest.mark.asyncio
async def test_execution_engine_submit_order():
    from app.execution.engine import ExecutionEngine
    engine = ExecutionEngine(broker_name="mock")
    await engine.start()
    engine.update_price("RELIANCE", 2800.0)
    result = await engine.submit_order(
        symbol="RELIANCE", side="buy", order_type="market",
        quantity=5, exchange="NSE",
    )
    assert result["status"] == "filled"
    await engine.stop()


@pytest.mark.asyncio
async def test_execution_engine_risk_check():
    from app.execution.engine import ExecutionEngine, RiskCheckFailed
    engine = ExecutionEngine(broker_name="mock", risk_config={
        "max_daily_loss": 5000,
        "max_order_value": 100,  # very low limit
        "max_open_positions": 10,
        "symbol_blacklist": [],
        "allowed_hours_start": None,
        "allowed_hours_end": None,
    })
    await engine.start()
    engine.update_price("RELIANCE", 2800.0)
    with pytest.raises(RiskCheckFailed):
        await engine.submit_order("RELIANCE", "buy", "market", 10, exchange="NSE")
    await engine.stop()


@pytest.mark.asyncio
async def test_bot_manager_start_stop():
    from app.execution.bot_manager import BotManager
    bm = BotManager()
    status = await bm.start_bot(
        bot_id="test-1", bot_name="Test Bot",
        strategy_dsl={}, symbol="RELIANCE", exchange="NSE",
    )
    assert status["status"] == "running"
    result = await bm.stop_bot("test-1")
    assert result is True


@pytest.mark.asyncio
async def test_bot_manager_kill_all():
    from app.execution.bot_manager import BotManager
    bm = BotManager()
    await bm.start_bot("b1", "Bot1", {}, "RELIANCE", "NSE")
    await bm.start_bot("b2", "Bot2", {}, "TCS", "NSE")
    assert bm.active_count == 2
    stopped = await bm.stop_all()
    assert stopped == 2
    assert bm.active_count == 0


def test_risk_guard_validate():
    from app.risk.guard import RiskGuard
    guard = RiskGuard({
        "max_daily_loss": 5000,
        "max_order_value": 100000,
        "max_open_positions": 5,
        "symbol_blacklist": ["BADSTOCK"],
    })
    violations = guard.validate_order("RELIANCE", "buy", 10, 2800.0, current_positions=2)
    assert violations == []


def test_risk_guard_rejects_blacklisted():
    from app.risk.guard import RiskGuard
    guard = RiskGuard({"max_daily_loss": 5000, "max_order_value": 50000,
                       "max_open_positions": 10, "symbol_blacklist": ["BADSTOCK"]})
    violations = guard.validate_order("BADSTOCK", "buy", 1, 100.0, current_positions=0)
    assert len(violations) > 0


def test_risk_guard_rejects_oversized_order():
    from app.risk.guard import RiskGuard
    guard = RiskGuard({"max_daily_loss": 5000, "max_order_value": 1000,
                       "symbol_blacklist": [], "max_open_positions": 10})
    violations = guard.validate_order("RELIANCE", "buy", 100, 2800.0, current_positions=0)
    assert len(violations) > 0
