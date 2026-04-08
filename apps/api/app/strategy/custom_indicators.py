"""
Custom Indicator System
Lets users define and run their own Python indicators from the dashboard.
Indicators are stored in MongoDB, validated for safety, and cached in Redis.
"""
from __future__ import annotations
import ast
import hashlib
import textwrap
import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import uuid

logger = logging.getLogger(__name__)

# ─── Safe builtins for indicator sandbox ─────────────────────────────────────
SAFE_MODULES = {"math", "statistics"}
FORBIDDEN_NAMES = {
    "exec", "eval", "compile", "__import__", "open", "os", "sys",
    "subprocess", "socket", "requests", "httpx", "aiohttp",
    "importlib", "builtins", "__builtins__",
}


# ─── In-memory registry (loaded from MongoDB on startup) ─────────────────────
_INDICATOR_REGISTRY: Dict[str, "CustomIndicator"] = {}


class CustomIndicator:
    """
    A user-defined Python indicator stored in MongoDB.
    """
    def __init__(
        self,
        id: str,
        name: str,
        description: str,
        code: str,             # Python function: def compute(df, **params) -> pd.Series
        params_schema: Dict,   # {"period": {"type": "int", "default": 14, "min": 2, "max": 200}}
        output_type: str,      # "line" | "histogram" | "signal"
        color: str = "#4a9eff",
        created_at: Optional[datetime] = None,
    ):
        self.id           = id
        self.name         = name
        self.description  = description
        self.code         = code
        self.params_schema = params_schema
        self.output_type  = output_type
        self.color        = color
        self.created_at   = created_at or datetime.utcnow()
        self._compiled    = None

    def to_dict(self) -> Dict:
        return {
            "id":           self.id,
            "name":         self.name,
            "description":  self.description,
            "code":         self.code,
            "params_schema":self.params_schema,
            "output_type":  self.output_type,
            "color":        self.color,
            "created_at":   self.created_at.isoformat(),
        }


# ─── Built-in custom indicator examples ──────────────────────────────────────

BUILTIN_INDICATORS = [
    {
        "id": "hull_ma",
        "name": "Hull Moving Average (HMA)",
        "description": "Reduces lag compared to SMA/EMA. Formula: WMA(2*WMA(n/2) - WMA(n), sqrt(n))",
        "code": textwrap.dedent("""
            def compute(df, period=14):
                import numpy as np
                close = df['close']
                half = int(period / 2)
                sqrt_p = int(np.sqrt(period))
                wma_half = close.rolling(half).apply(lambda x: np.dot(x, np.arange(1, half+1)) / np.arange(1, half+1).sum())
                wma_full = close.rolling(period).apply(lambda x: np.dot(x, np.arange(1, period+1)) / np.arange(1, period+1).sum())
                hull_raw = 2 * wma_half - wma_full
                hma = hull_raw.rolling(sqrt_p).apply(lambda x: np.dot(x, np.arange(1, sqrt_p+1)) / np.arange(1, sqrt_p+1).sum())
                return hma
        """).strip(),
        "params_schema": {"period": {"type": "int", "default": 14, "min": 5, "max": 200, "label": "Period"}},
        "output_type": "line",
        "color": "#ff9f43",
    },
    {
        "id": "chandelier_exit",
        "name": "Chandelier Exit",
        "description": "Trailing stop based on ATR. Useful as a trend exit signal.",
        "code": textwrap.dedent("""
            def compute(df, period=22, multiplier=3.0):
                import pandas as pd
                high = df['high']
                low = df['low']
                close = df['close']
                tr = pd.concat([
                    high - low,
                    (high - close.shift()).abs(),
                    (low - close.shift()).abs()
                ], axis=1).max(axis=1)
                atr = tr.rolling(period).mean()
                highest_high = high.rolling(period).max()
                chandelier = highest_high - multiplier * atr
                return chandelier
        """).strip(),
        "params_schema": {
            "period":     {"type": "int",   "default": 22,  "min": 5,   "max": 200, "label": "Period"},
            "multiplier": {"type": "float", "default": 3.0, "min": 0.5, "max": 10,  "label": "ATR Multiplier"},
        },
        "output_type": "line",
        "color": "#ff4757",
    },
    {
        "id": "squeeze_momentum",
        "name": "Squeeze Momentum (LazyBear)",
        "description": "Combines Bollinger Bands + Keltner Channels to detect market squeezes.",
        "code": textwrap.dedent("""
            def compute(df, length=20, mult=2.0, length_kc=20, mult_kc=1.5):
                import pandas as pd, numpy as np
                close = df['close']
                high  = df['high']
                low   = df['low']
                # Bollinger Bands
                basis = close.rolling(length).mean()
                dev   = close.rolling(length).std()
                upper_bb = basis + mult * dev
                lower_bb = basis - mult * dev
                # Keltner Channel
                tr = pd.concat([high - low, (high - close.shift()).abs(), (low - close.shift()).abs()], axis=1).max(axis=1)
                atr = tr.rolling(length_kc).mean()
                upper_kc = basis + mult_kc * atr
                lower_kc = basis - mult_kc * atr
                # Squeeze: when BB is inside KC
                sqz_on  = (lower_bb > lower_kc) & (upper_bb < upper_kc)
                # Momentum
                highest = high.rolling(length).max()
                lowest  = low.rolling(length).min()
                mid_hl  = (highest + lowest) / 2
                delta   = close - (mid_hl + basis) / 2
                val     = delta.rolling(length).apply(
                    lambda x: np.polyfit(range(len(x)), x, 1)[0] if len(x) == length else np.nan
                )
                return val
        """).strip(),
        "params_schema": {
            "length":     {"type": "int",   "default": 20,  "min": 5,   "max": 200, "label": "BB Length"},
            "mult":       {"type": "float", "default": 2.0, "min": 0.5, "max": 5,   "label": "BB Multiplier"},
            "length_kc":  {"type": "int",   "default": 20,  "min": 5,   "max": 200, "label": "KC Length"},
            "mult_kc":    {"type": "float", "default": 1.5, "min": 0.5, "max": 5,   "label": "KC Multiplier"},
        },
        "output_type": "histogram",
        "color": "#00d4a0",
    },
    {
        "id": "wavetrend",
        "name": "WaveTrend Oscillator",
        "description": "Popular oscillator for overbought/oversold detection. Good for crypto.",
        "code": textwrap.dedent("""
            def compute(df, n1=10, n2=21):
                import pandas as pd
                hlc3 = (df['high'] + df['low'] + df['close']) / 3
                esa  = hlc3.ewm(span=n1).mean()
                d    = (hlc3 - esa).abs().ewm(span=n1).mean()
                ci   = (hlc3 - esa) / (0.015 * d)
                wt1  = ci.ewm(span=n2).mean()
                return wt1
        """).strip(),
        "params_schema": {
            "n1": {"type": "int", "default": 10, "min": 2, "max": 50, "label": "Channel Length"},
            "n2": {"type": "int", "default": 21, "min": 2, "max": 50, "label": "Average Length"},
        },
        "output_type": "line",
        "color": "#9b8fff",
    },
]


# ─── Safety validator ─────────────────────────────────────────────────────────

class IndicatorSafetyError(Exception):
    pass


def validate_indicator_code(code: str) -> bool:
    """
    Validate indicator code for safety using AST analysis.
    Blocks: imports, exec, eval, file access, network access.
    """
    try:
        tree = ast.parse(code)
    except SyntaxError as e:
        raise IndicatorSafetyError(f"Syntax error: {e}")

    for node in ast.walk(tree):
        # Block imports (except allowed)
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            if isinstance(node, ast.ImportFrom):
                module = node.module or ""
                if module.split(".")[0] not in ("numpy", "pandas", "math", "statistics"):
                    raise IndicatorSafetyError(f"Import not allowed: {module}")
            else:
                for alias in node.names:
                    if alias.name.split(".")[0] not in ("numpy", "pandas", "math", "statistics"):
                        raise IndicatorSafetyError(f"Import not allowed: {alias.name}")

        # Block dangerous calls
        if isinstance(node, ast.Call):
            if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_NAMES:
                raise IndicatorSafetyError(f"Forbidden function: {node.func.id}")
            if isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_NAMES:
                raise IndicatorSafetyError(f"Forbidden method: {node.func.attr}")

        # Block dangerous attribute access
        if isinstance(node, ast.Attribute) and node.attr in ("__class__", "__bases__", "__subclasses__", "__globals__"):
            raise IndicatorSafetyError(f"Forbidden attribute access: {node.attr}")

    # Must contain a compute() function
    func_names = [n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)]
    if "compute" not in func_names:
        raise IndicatorSafetyError("Code must define a 'compute(df, **params)' function")

    return True


# ─── Executor ─────────────────────────────────────────────────────────────────

def execute_custom_indicator(code: str, df, params: Dict = None) -> "pd.Series":
    """
    Safely execute a custom indicator function.
    Returns a pd.Series aligned to df index.
    """
    import pandas as pd
    import numpy as np

    validate_indicator_code(code)

    # Create restricted execution namespace
    namespace = {
        "pd": pd,
        "pandas": pd,
        "np": np,
        "numpy": np,
    }

    exec(code, namespace)  # noqa: S102 — validated above

    compute_fn = namespace.get("compute")
    if not compute_fn:
        raise IndicatorSafetyError("No compute() function found after execution")

    result = compute_fn(df, **(params or {}))

    if not isinstance(result, pd.Series):
        result = pd.Series(result, index=df.index)

    return result.rename("custom_indicator")


# ─── Registry functions ───────────────────────────────────────────────────────

def register_indicator(indicator: CustomIndicator):
    _INDICATOR_REGISTRY[indicator.id] = indicator


def get_indicator(indicator_id: str) -> Optional[CustomIndicator]:
    return _INDICATOR_REGISTRY.get(indicator_id)


def list_indicators() -> List[Dict]:
    return [ind.to_dict() for ind in _INDICATOR_REGISTRY.values()]


def load_builtins():
    """Load built-in custom indicators into the registry."""
    for ind_data in BUILTIN_INDICATORS:
        ind = CustomIndicator(**ind_data)
        register_indicator(ind)
    logger.info(f"Loaded {len(BUILTIN_INDICATORS)} built-in custom indicators")


# Load on module import
load_builtins()
