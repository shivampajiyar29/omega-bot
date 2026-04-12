"""Tests for Strategy DSL and sample strategies."""
import pytest


def test_sample_strategies_exist():
    from app.strategy.dsl import SAMPLE_STRATEGIES
    assert len(SAMPLE_STRATEGIES) > 0


def test_ema_crossover_structure():
    from app.strategy.dsl import SAMPLE_STRATEGIES
    s = SAMPLE_STRATEGIES.get("ema_crossover")
    assert s is not None
    assert "indicators" in s
    assert "entry" in s
    assert "exits" in s


def test_strategy_dsl_validates():
    from app.strategy.dsl import StrategyDSL, SAMPLE_STRATEGIES
    for name, dsl in SAMPLE_STRATEGIES.items():
        if dsl:
            validated = StrategyDSL(**dsl)
            assert validated.name or validated.version


def test_custom_indicator_list():
    from app.strategy.custom_indicators import list_indicators
    indicators = list_indicators()
    assert isinstance(indicators, list)
    assert len(indicators) > 0


def test_custom_indicator_has_required_fields():
    from app.strategy.custom_indicators import list_indicators
    for ind in list_indicators():
        assert "id" in ind
        assert "name" in ind
        assert "code" in ind


def test_indicator_code_validation():
    from app.strategy.custom_indicators import validate_indicator_code, IndicatorSafetyError
    good = "def compute(df, period=14):\n    return df['close'].rolling(period).mean()"
    assert validate_indicator_code(good) is True


def test_dangerous_code_rejected():
    from app.strategy.custom_indicators import validate_indicator_code, IndicatorSafetyError
    bad = "def compute(df):\n    import os\n    return df['close']"
    with pytest.raises(IndicatorSafetyError):
        validate_indicator_code(bad)
