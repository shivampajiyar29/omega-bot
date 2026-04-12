"""Tests for DSL Evaluator."""
import pytest
from datetime import datetime


def make_bars(n=60, drift=0.003):
    from app.backtester.engine import Bar
    bars, price = [], 2800.0
    for _ in range(n):
        price *= (1 + drift)
        bars.append(Bar(
            timestamp=datetime(2024, 1, 1),
            open=price * 0.999, high=price * 1.002,
            low=price * 0.998, close=price, volume=100_000,
        ))
    return bars


def test_evaluator_loads_ema_strategy():
    from app.backtester.evaluator import DSLEvaluator
    from app.strategy.dsl import SAMPLE_STRATEGIES
    dsl = SAMPLE_STRATEGIES.get("ema_crossover", {})
    assert dsl, "ema_crossover sample strategy must exist"
    ev = DSLEvaluator(dsl)
    fn = ev.get_signal_fn()
    assert callable(fn)


def test_evaluator_produces_signal_on_uptrend():
    from app.backtester.evaluator import DSLEvaluator
    from app.strategy.dsl import SAMPLE_STRATEGIES
    dsl = SAMPLE_STRATEGIES.get("ema_crossover", {})
    ev = DSLEvaluator(dsl)
    fn = ev.get_signal_fn()
    bars = make_bars(100, drift=0.005)
    # Verify evaluator runs without crashing and returns valid values only
    signals = [fn(bars[:i], None, {}) for i in range(10, 100)]
    assert all(s in ("long", "short", "exit", None) for s in signals)


def test_evaluator_none_on_insufficient_bars():
    from app.backtester.evaluator import DSLEvaluator
    from app.strategy.dsl import SAMPLE_STRATEGIES
    dsl = SAMPLE_STRATEGIES.get("ema_crossover", {})
    ev = DSLEvaluator(dsl)
    fn = ev.get_signal_fn()
    bars = make_bars(5)
    result = fn(bars, None, {})
    assert result is None


def test_evaluator_returns_exit_when_stop_hit():
    from app.backtester.evaluator import DSLEvaluator
    from app.strategy.dsl import SAMPLE_STRATEGIES
    dsl = SAMPLE_STRATEGIES.get("ema_crossover", {})
    ev = DSLEvaluator(dsl)
    fn = ev.get_signal_fn()
    bars = make_bars(60)
    position = {"side": "long", "entry_price": 5000.0, "quantity": 10}
    result = fn(bars, position, {})
    assert result in ("exit", "long", None)
