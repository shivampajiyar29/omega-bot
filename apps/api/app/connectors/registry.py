"""
Connector Registry — maps adapter names to their classes.

ADD NEW BROKERS HERE. This is the only file you need to edit.
Each broker is a Python class in apps/api/app/adapters/broker/

To add a new broker:
1. Create apps/api/app/adapters/broker/your_broker.py
2. Subclass BaseBrokerAdapter
3. Add a _try_register_broker() call below
4. Restart API: make restart-api
5. Enable via Connectors page in the UI
"""
from typing import Dict, Type
import logging

from app.adapters.broker.mock_broker import MockBrokerAdapter, BaseBrokerAdapter
from app.adapters.marketdata.mock_data import MockMarketDataAdapter, CSVDataAdapter

logger = logging.getLogger(__name__)

BROKER_REGISTRY: Dict[str, Type] = {
    "mock": MockBrokerAdapter,
}

MARKETDATA_REGISTRY: Dict[str, Type] = {
    "mock": MockMarketDataAdapter,
    "csv":  CSVDataAdapter,
}


def _try_register_broker(name: str, module_path: str, class_name: str):
    """Register a broker adapter, silently skipping if dependencies aren't installed."""
    try:
        import importlib
        mod = importlib.import_module(module_path)
        cls = getattr(mod, class_name)
        BROKER_REGISTRY[name] = cls
        logger.debug(f"Registered broker adapter: {name}")
    except ImportError as e:
        logger.debug(f"Skipping broker '{name}' — missing dependency: {e}")
    except Exception as e:
        logger.warning(f"Failed to register broker '{name}': {e}")


# ─── Register all broker adapters ─────────────────────────────────────────────
# Indian brokers
_try_register_broker("zerodha",   "app.adapters.broker.zerodha",   "ZerodhaBrokerAdapter")
_try_register_broker("angel_one", "app.adapters.broker.angel_one", "AngelOneBrokerAdapter")
_try_register_broker("dhan",      "app.adapters.broker.dhan",      "DhanBrokerAdapter")
_try_register_broker("upstox",    "app.adapters.broker.upstox",    "UpstoxBrokerAdapter")

# US brokers
_try_register_broker("alpaca",    "app.adapters.broker.alpaca",    "AlpacaBrokerAdapter")

# Crypto
_try_register_broker("binance",   "app.adapters.broker.binance",   "BinanceBrokerAdapter")

# Add future brokers here:
# _try_register_broker("ibkr",     "app.adapters.broker.ibkr",     "IBKRBrokerAdapter")
# _try_register_broker("fyers",    "app.adapters.broker.fyers",    "FyersBrokerAdapter")
# _try_register_broker("groww",    "app.adapters.broker.groww",    "GrowwBrokerAdapter")


# ─── Adapter factory functions ────────────────────────────────────────────────

def get_broker_adapter(name: str, config: dict = None) -> BaseBrokerAdapter:
    """Instantiate a broker adapter by name. Raises ValueError if not registered."""
    cls = BROKER_REGISTRY.get(name)
    if not cls:
        available = sorted(BROKER_REGISTRY.keys())
        raise ValueError(
            f"Unknown broker adapter: '{name}'. "
            f"Available: {available}. "
            f"Add it to apps/api/app/connectors/registry.py"
        )
    return cls(config=config or {})


def get_marketdata_adapter(name: str, config: dict = None):
    """Instantiate a market data adapter by name."""
    cls = MARKETDATA_REGISTRY.get(name)
    if not cls:
        available = sorted(MARKETDATA_REGISTRY.keys())
        raise ValueError(f"Unknown market data adapter: '{name}'. Available: {available}")
    return cls(config=config or {})


def list_brokers() -> list:
    """Return metadata for all registered broker adapters."""
    return [
        {
            "name":              name,
            "display_name":      getattr(cls, "DISPLAY_NAME",     name.replace("_", " ").title()),
            "supported_markets": getattr(cls, "SUPPORTED_MARKETS", []),
            "registered":        True,
        }
        for name, cls in sorted(BROKER_REGISTRY.items())
    ]


def list_marketdata_adapters() -> list:
    """Return metadata for all registered market data adapters."""
    return [
        {
            "name":         name,
            "display_name": getattr(cls, "DISPLAY_NAME", name.title()),
        }
        for name, cls in sorted(MARKETDATA_REGISTRY.items())
    ]
