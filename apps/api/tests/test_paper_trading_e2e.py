"""
Paper Trading End-to-End Verification Tests
Tests the complete flow: price update → signal → order → fill → position → P&L

Run with: pytest tests/test_paper_trading_e2e.py -v
"""
import asyncio
import pytest
from datetime import datetime


class TestPaperTradingFlow:
    """
    Complete paper trading pipeline verification.
    These tests prove paper trading works end-to-end without a broker.
    """

    @pytest.fixture
    async def broker(self):
        from app.adapters.broker.mock_broker import MockBrokerAdapter
        b = MockBrokerAdapter(config={
            "initial_capital":  500_000.0,
            "slippage_pct":     0.01,
            "commission_pct":   0.03,
            "fill_delay_ms":    0,        # instant fills in test
        })
        await b.connect()
        b.update_price("RELIANCE", 2800.00)
        b.update_price("TCS",      3900.00)
        b.update_price("NIFTY50",  24800.00)
        yield b
        await b.disconnect()

    # ─── Basic order lifecycle ──────────────────────────────────────────────

    @pytest.mark.asyncio
    async def test_market_buy_fills_immediately(self, broker):
        order = await broker.place_order("RELIANCE", "buy", "market", 10)
        assert order.status == "filled", "Market order must fill immediately"
        assert order.filled_quantity == 10
        assert order.avg_fill_price > 0

    @pytest.mark.asyncio
    async def test_buy_reduces_cash(self, broker):
        acct_before = await broker.get_account()
        order = await broker.place_order("RELIANCE", "buy", "market", 50)
        acct_after = await broker.get_account()

        expected_cost = order.avg_fill_price * 50 * (1 + 0.0003)  # price + commission
        actual_reduction = acct_before["cash"] - acct_after["cash"]
        assert abs(actual_reduction - expected_cost) < 10, "Cash reduction must match order cost + commission"

    @pytest.mark.asyncio
    async def test_position_created_after_buy(self, broker):
        await broker.place_order("RELIANCE", "buy", "market", 25)
        pos = await broker.get_position("RELIANCE")
        assert pos is not None
        assert pos.quantity == 25
        assert pos.side == "buy"
        assert pos.avg_price > 0

    @pytest.mark.asyncio
    async def test_position_pnl_updates_with_price(self, broker):
        await broker.place_order("RELIANCE", "buy", "market", 10)
        pos_before = await broker.get_position("RELIANCE")

        # Simulate price increase
        broker.update_price("RELIANCE", 3000.00)
        pos_after = await broker.get_position("RELIANCE")

        assert pos_after.current_price == 3000.00
        assert pos_after.unrealized_pnl > 0, "P&L should be positive after price rise"
        assert pos_after.unrealized_pnl > pos_before.unrealized_pnl

    @pytest.mark.asyncio
    async def test_sell_closes_position(self, broker):
        await broker.place_order("RELIANCE", "buy", "market", 10)
        await broker.place_order("RELIANCE", "sell", "market", 10)
        pos = await broker.get_position("RELIANCE")
        assert pos is None, "Position should be closed after full sell"

    @pytest.mark.asyncio
    async def test_cash_recovered_after_profitable_close(self, broker):
        acct_initial = await broker.get_account()
        await broker.place_order("RELIANCE", "buy", "market", 10)

        # Raise price before selling
        broker.update_price("RELIANCE", 3200.00)
        await broker.place_order("RELIANCE", "sell", "market", 10)

        acct_final = await broker.get_account()
        # Cash should be MORE than initial because we made a profit
        assert acct_final["cash"] > acct_initial["cash"] - 1, "Profitable trade should increase net equity"

    @pytest.mark.asyncio
    async def test_limit_order_stays_open(self, broker):
        order = await broker.place_order("RELIANCE", "buy", "limit", 10, price=2600.00)
        assert order.status == "open", "Limit order below market should stay open"

    @pytest.mark.asyncio
    async def test_cancel_open_order(self, broker):
        order = await broker.place_order("RELIANCE", "buy", "limit", 5, price=2500.00)
        assert order.status == "open"
        cancelled = await broker.cancel_order(order.id)
        assert cancelled is True
        refreshed = await broker.get_order(order.id)
        assert refreshed.status == "cancelled"

    @pytest.mark.asyncio
    async def test_insufficient_funds_rejected(self, broker):
        """Order that exceeds available cash should be rejected."""
        acct = await broker.get_account()
        # Try to buy way more than we can afford
        huge_qty = int(acct["cash"] / 2800.0) * 10
        order = await broker.place_order("RELIANCE", "buy", "market", huge_qty)
        assert order.status == "rejected", "Order exceeding capital should be rejected"

    @pytest.mark.asyncio
    async def test_multiple_symbols_tracked(self, broker):
        await broker.place_order("RELIANCE", "buy", "market", 10)
        await broker.place_order("TCS",      "buy", "market", 5)

        positions = await broker.get_positions()
        symbols = [p.symbol for p in positions]
        assert "RELIANCE" in symbols
        assert "TCS" in symbols
        assert len(positions) == 2

    @pytest.mark.asyncio
    async def test_portfolio_value_sums_correctly(self, broker):
        await broker.place_order("RELIANCE", "buy", "market", 10)
        await broker.place_order("TCS",      "buy", "market", 5)

        acct = await broker.get_account()
        positions = await broker.get_positions()

        positions_value = sum(p.current_price * p.quantity for p in positions)
        total_expected = acct["cash"] + positions_value
        assert abs(acct["total_value"] - total_expected) < 1.0, "Total value = cash + positions"

    # ─── Execution engine integration ──────────────────────────────────────

    @pytest.mark.asyncio
    async def test_execution_engine_places_order(self):
        from app.execution.engine import ExecutionEngine
        engine = ExecutionEngine(broker_name="mock", risk_config={
            "max_daily_loss":    50_000,
            "max_order_value":   100_000,
            "max_open_positions": 20,
            "symbol_blacklist":  [],
            "allowed_hours_start": None,
            "allowed_hours_end":   None,
        })
        await engine.start()
        engine.update_price("RELIANCE", 2800.0)

        order = await engine.submit_order(
            symbol="RELIANCE", side="buy", order_type="market",
            quantity=10, exchange="NSE",
        )
        assert order["status"] == "filled"
        await engine.stop()

    @pytest.mark.asyncio
    async def test_kill_switch_blocks_orders(self):
        from app.execution.engine import ExecutionEngine, RiskCheckFailed
        engine = ExecutionEngine(broker_name="mock", risk_config={
            "max_daily_loss": 1,  # Effectively immediate block
            "max_order_value": 100_000,
            "max_open_positions": 20,
            "symbol_blacklist": [],
            "allowed_hours_start": None,
            "allowed_hours_end": None,
        })
        await engine.start()
        engine._daily_pnl = -5000  # Simulate big loss

        with pytest.raises(RiskCheckFailed):
            await engine.submit_order("RELIANCE", "buy", "market", 10, exchange="NSE")

        await engine.stop()

    # ─── Strategy signal → paper trade ─────────────────────────────────────

    @pytest.mark.asyncio
    async def test_ema_crossover_generates_signal(self):
        """Test that EMA crossover strategy produces buy/sell signals on suitable data."""
        from app.backtester.evaluator import DSLEvaluator
        from app.strategy.dsl import SAMPLE_STRATEGIES
        from app.backtester.engine import Bar
        import math

        evaluator = DSLEvaluator(SAMPLE_STRATEGIES["ema_crossover"])
        signal_fn = evaluator.get_signal_fn()

        # Generate a strongly trending bar series
        bars = []
        price = 2700.0
        for i in range(60):
            price *= 1.003  # 0.3% per bar uptrend
            bars.append(Bar(
                timestamp=datetime.utcnow(),
                open=price * 0.999, high=price * 1.002,
                low=price * 0.998, close=price, volume=100_000,
            ))

        # Should eventually produce a long signal on an uptrend
        signals = []
        for i in range(25, len(bars)):
            sig = signal_fn(bars[:i], None, {})
            if sig:
                signals.append(sig)

        # In a consistent uptrend, EMA crossover should signal long
        assert any(s == "long" for s in signals), \
            "EMA crossover must produce a long signal on an uptrend"

    @pytest.mark.asyncio
    async def test_backtest_produces_results(self):
        """Quick backtest smoke test — verifies the engine returns valid metrics."""
        from app.backtester.engine import BacktestEngine, Bar
        from app.strategy.dsl import SAMPLE_STRATEGIES
        from app.backtester.evaluator import DSLEvaluator

        # Build 100 bars
        bars, price = [], 2800.0
        for i in range(100):
            import random
            price *= 1 + random.gauss(0.001, 0.008)
            bars.append(Bar(
                timestamp=datetime.utcnow(),
                open=price, high=price*1.003, low=price*0.997, close=price, volume=50_000
            ))

        evaluator = DSLEvaluator(SAMPLE_STRATEGIES["ema_crossover"])

        engine = BacktestEngine(
            bars=bars,
            strategy_fn=evaluator.get_signal_fn(),
            symbol="RELIANCE",
            timeframe="15m",
            initial_capital=100_000,
            commission_pct=0.03,
            slippage_pct=0.01,
        )
        results = engine.run()

        # Structural checks
        assert results.initial_capital == 100_000
        assert results.total_trades >= 0
        assert isinstance(results.sharpe_ratio, float)
        assert 0 <= results.win_rate_pct <= 100
        assert len(results.equity_curve) == 100
        assert results.total_trades == results.winning_trades + results.losing_trades
