"""
Endpoint module exports — maps router imports in v1/router.py.
Each sub-module exposes a `router = APIRouter()` object.
"""
# Re-export all the sub-routers from the stubs defined in __init__.py
from app.api.v1.endpoints import (
    orders as _orders,
    positions as _positions,
    alerts as _alerts,
    logs as _logs,
    modules as _modules,
)
from app.api.v1.endpoints import (
    settings_router,
    watchlist_router,
    connectors_router,
    portfolio_router,
    marketdata_router,
    webhooks_router,
)

# Create proper APIRouter instances with the right names for import
import types
import sys

def _make_module(name: str, router) -> types.ModuleType:
    mod = types.ModuleType(f"app.api.v1.endpoints.{name}")
    mod.router = router
    sys.modules[mod.__name__] = mod
    return mod

_make_module("orders",    _orders.router if hasattr(_orders, "router") else _orders)
_make_module("positions", _positions.router if hasattr(_positions, "router") else _positions)
_make_module("alerts",    _alerts.router if hasattr(_alerts, "router") else _alerts)
_make_module("logs",      _logs.router if hasattr(_logs, "router") else _logs)
_make_module("modules",   _modules.router if hasattr(_modules, "router") else _modules)
_make_module("settings",  settings_router)
_make_module("watchlist", watchlist_router)
_make_module("connectors", connectors_router)
_make_module("portfolio", portfolio_router)
_make_module("marketdata", marketdata_router)
_make_module("webhooks",  webhooks_router)
