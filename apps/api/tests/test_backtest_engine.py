"""Tests for Backtesting Engine."""
import pytest
from datetime import datetime


def make_bars(n=100, start_price=2800.0, drift=0.001):
    from app.backtester.engine import Bar
    bars = []
    price = start_price
    for i in range(n):
        price *= (1 + drift)
        bars.append(Bar(
            timestamp=datetime(2024, 1, 1),
            open=price * 0.999,
            high=price * 1.002,
            low=price * 0.998,
            close=price,
            volume=100_000,
        ))
    return bars


def always_long(bars, position, params):
    if position is None and len(bars) > 10:
        return "long"
    if position is not None and len(bars) > 50:
        return "exit"
    return None


def buy_and_hold(bars, position, params):
    if position is None and len(bars) == 1:
        return "long"
    return None


def test_engine_runs():
    from app.backtester.engine import BacktestEngine
    bars = make_bars(100)
    engine = BacktestEngine(bars=bars, strategy_fn=always_long, initial_capital=100_000)
    results = engine.run()
    assert results.initial_capital == 100_000
    assert results.total_trades >= 0
    assert len(results.equity_curve) == 100


def test_equity_curve_length():
    from app.backtester.engine import BacktestEngine
    bars = make_bars(50)
    engine = BacktestEngine(bars=bars, strategy_fn=buy_and_hold, initial_capital=100_000)
    results = engine.run()
    assert len(results.equity_curve) == 50


def test_profitable_on_uptrend():
    from app.backtester.engine import BacktestEngine
    bars = make_bars(60, drift=0.005)  # strong uptrend
    engine = BacktestEngine(bars=bars, strategy_fn=buy_and_hold, initial_capital=100_000)
    results = engine.run()
    assert results.total_return_pct > 0


def test_metrics_structure():
    from app.backtester.engine import BacktestEngine
    bars = make_bars(100)
    engine = BacktestEngine(bars=bars, strategy_fn=always_long, initial_capital=50_000)
    results = engine.run()
    assert hasattr(results, "sharpe_ratio")
    assert hasattr(results, "max_drawdown_pct")
    assert hasattr(results, "win_rate_pct")
    assert 0 <= results.win_rate_pct <= 100


def test_trade_log_format():
    from app.backtester.engine import BacktestEngine
    bars = make_bars(100)
    engine = BacktestEngine(bars=bars, strategy_fn=always_long, initial_capital=100_000)
    results = engine.run()
    for trade in results.trade_log:
        assert "entry_price" in trade
        assert "side" in trade
        assert "pnl" in trade


def test_empty_strategy_no_trades():
    from app.backtester.engine import BacktestEngine
    bars = make_bars(100)
    engine = BacktestEngine(bars=bars, strategy_fn=lambda b, p, _: None, initial_capital=100_000)
    results = engine.run()
    assert results.total_trades == 0
    assert results.final_capital == results.initial_capital
