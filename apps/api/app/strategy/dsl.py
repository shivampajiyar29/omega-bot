"""
Minimal strategy DSL schema and built-in samples used across the API.
"""
from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, ConfigDict, Field


class IndicatorRef(BaseModel):
    indicator_id: str
    field: Optional[str] = None


class ValueRef(BaseModel):
    value: float | int


class Condition(BaseModel):
    left: Dict[str, Any]
    operator: str
    right: Dict[str, Any]


class RuleGroup(BaseModel):
    logic: Literal["and", "or"] = "and"
    conditions: List[Condition] = Field(default_factory=list)


class EntryRules(BaseModel):
    long: Optional[RuleGroup] = None
    short: Optional[RuleGroup] = None


class IndicatorSpec(BaseModel):
    id: str
    type: str
    params: Dict[str, Any] = Field(default_factory=dict)


class ExitSpec(BaseModel):
    type: str
    value: Optional[float | int] = None
    unit: Optional[str] = None
    params: Dict[str, Any] = Field(default_factory=dict)


class SizingSpec(BaseModel):
    method: str
    value: float | int


class StrategyDSL(BaseModel):
    model_config = ConfigDict(extra="allow")

    version: str
    name: str
    timeframe: str = "15m"
    indicators: List[IndicatorSpec] = Field(default_factory=list)
    entry: EntryRules
    exits: List[ExitSpec] = Field(default_factory=list)
    sizing: Optional[SizingSpec] = None


SAMPLE_STRATEGIES: Dict[str, Dict[str, Any]] = {
    "ema_crossover": {
        "version": "1.0",
        "name": "EMA 9/21 Crossover",
        "timeframe": "15m",
        "indicators": [
            {"id": "ema9", "type": "ema", "params": {"period": 9}},
            {"id": "ema21", "type": "ema", "params": {"period": 21}},
        ],
        "entry": {
            "long": {
                "logic": "and",
                "conditions": [
                    {
                        "left": {"indicator_id": "ema9"},
                        "operator": "crosses_above",
                        "right": {"indicator_id": "ema21"},
                    }
                ],
            }
        },
        "exits": [
            {"type": "fixed_stop", "value": 1.5, "unit": "pct"},
            {"type": "fixed_target", "value": 3.0, "unit": "pct"},
        ],
        "sizing": {"method": "fixed_value", "value": 25000},
    },
    "rsi_breakout": {
        "version": "1.0",
        "name": "RSI Breakout",
        "timeframe": "15m",
        "indicators": [
            {"id": "rsi14", "type": "rsi", "params": {"period": 14}},
        ],
        "entry": {
            "long": {
                "logic": "and",
                "conditions": [
                    {
                        "left": {"indicator_id": "rsi14"},
                        "operator": "greater_than",
                        "right": {"value": 60},
                    }
                ],
            }
        },
        "exits": [
            {"type": "fixed_stop", "value": 1.0, "unit": "pct"},
            {"type": "fixed_target", "value": 2.5, "unit": "pct"},
        ],
        "sizing": {"method": "fixed_value", "value": 20000},
    },
}
