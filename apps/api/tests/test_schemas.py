"""
Tests for Pydantic v2 schemas — input validation.
"""
import pytest
from pydantic import ValidationError
from app.schemas.schemas import (
    StrategyCreateSchema, BotCreateSchema, OrderPlaceSchema,
    BacktestCreateSchema, RiskProfileCreateSchema,
)
from app.strategy.dsl import SAMPLE_STRATEGIES


class TestStrategySchema:
    def test_valid_strategy(self):
        data = StrategyCreateSchema(
            name="EMA Test",
            dsl=SAMPLE_STRATEGIES["ema_crossover"],
            market_type="equity",
        )
        assert data.name == "EMA Test"

    def test_invalid_dsl_raises(self):
        with pytest.raises(ValidationError) as exc:
            StrategyCreateSchema(
                name="Bad",
                dsl={"version": "1.0", "name": "x", "entry": {"bad": True}},
            )
        assert "DSL" in str(exc.value) or "dsl" in str(exc.value).lower()

    def test_empty_name_raises(self):
        with pytest.raises(ValidationError):
            StrategyCreateSchema(name="", dsl=SAMPLE_STRATEGIES["ema_crossover"])

    def test_symbol_uppercased_in_bot(self):
        # BotCreateSchema auto-uppercases symbol
        data = BotCreateSchema(
            name="Test Bot",
            strategy_id="s-123",
            connector_id="c-456",
            symbol="reliance",
            exchange="nse",
        )
        assert data.symbol == "RELIANCE"
        assert data.exchange == "NSE"


class TestOrderSchema:
    def test_valid_market_order(self):
        o = OrderPlaceSchema(symbol="TCS", side="buy", quantity=10)
        assert o.symbol == "TCS"
        assert o.quantity == 10

    def test_zero_quantity_raises(self):
        with pytest.raises(ValidationError):
            OrderPlaceSchema(symbol="TCS", side="buy", quantity=0)

    def test_negative_price_raises(self):
        with pytest.raises(ValidationError):
            OrderPlaceSchema(symbol="TCS", side="buy", quantity=10, price=-100)

    def test_symbol_uppercased(self):
        o = OrderPlaceSchema(symbol="reliance", side="sell", quantity=5)
        assert o.symbol == "RELIANCE"


class TestBacktestSchema:
    def test_valid_backtest(self):
        b = BacktestCreateSchema(
            strategy_id="s-123",
            symbol="RELIANCE",
            start_date="2024-01-01",
            end_date="2024-06-30",
            initial_capital=100000,
        )
        assert b.timeframe == "15m"
        assert b.commission_pct == 0.03

    def test_end_before_start_raises(self):
        with pytest.raises(ValidationError):
            BacktestCreateSchema(
                strategy_id="s-123",
                symbol="RELIANCE",
                start_date="2024-06-30",
                end_date="2024-01-01",
            )

    def test_invalid_date_format_raises(self):
        with pytest.raises(ValidationError):
            BacktestCreateSchema(
                strategy_id="s-123",
                symbol="RELIANCE",
                start_date="not-a-date",
                end_date="2024-06-30",
            )

    def test_negative_capital_raises(self):
        with pytest.raises(ValidationError):
            BacktestCreateSchema(
                strategy_id="s-123",
                symbol="RELIANCE",
                start_date="2024-01-01",
                end_date="2024-06-30",
                initial_capital=-1000,
            )


class TestRiskProfileSchema:
    def test_valid_profile(self):
        r = RiskProfileCreateSchema(
            name="Conservative",
            max_daily_loss=2000,
            max_trade_loss=500,
            max_open_positions=5,
            max_order_value=25000,
        )
        assert r.max_margin_pct == 80.0
        assert r.allowed_hours_start == "09:15"

    def test_zero_loss_limit_raises(self):
        with pytest.raises(ValidationError):
            RiskProfileCreateSchema(
                name="Test",
                max_daily_loss=0,
                max_trade_loss=100,
                max_open_positions=5,
                max_order_value=10000,
            )

    def test_over_100_margin_raises(self):
        with pytest.raises(ValidationError):
            RiskProfileCreateSchema(
                name="Test",
                max_daily_loss=5000,
                max_trade_loss=1000,
                max_open_positions=10,
                max_order_value=50000,
                max_margin_pct=150,
            )
