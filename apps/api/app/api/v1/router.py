"""
API v1 Router — registers all route groups.
"""
from fastapi import APIRouter

from app.api.v1.endpoints.dashboard    import router as dashboard_router
from app.api.v1.endpoints.strategies   import router as strategies_router
from app.api.v1.endpoints.bots         import router as bots_router
from app.api.v1.endpoints.orders       import router as orders_router
from app.api.v1.endpoints.positions    import router as positions_router
from app.api.v1.endpoints.backtests    import router as backtests_router
from app.api.v1.endpoints.connectors   import router as connectors_router
from app.api.v1.endpoints.watchlist    import router as watchlist_router
from app.api.v1.endpoints.portfolio    import router as portfolio_router
from app.api.v1.endpoints.risk         import router as risk_router
from app.api.v1.endpoints.settings     import router as settings_router
from app.api.v1.endpoints.modules      import router as modules_router
from app.api.v1.endpoints.marketdata   import router as marketdata_router
from app.api.v1.endpoints.alerts       import router as alerts_router
from app.api.v1.endpoints.logs         import router as logs_router
from app.api.v1.endpoints.ai_assistant import router as ai_router
from app.api.v1.endpoints.webhooks     import router as webhooks_router
from app.api.v1.endpoints.indicators   import router as indicators_router
from app.api.v1.websockets             import router as ws_router

api_router = APIRouter()

api_router.include_router(dashboard_router,   prefix="/dashboard",   tags=["dashboard"])
api_router.include_router(strategies_router,  prefix="/strategies",  tags=["strategies"])
api_router.include_router(bots_router,        prefix="/bots",        tags=["bots"])
api_router.include_router(orders_router,      prefix="/orders",      tags=["orders"])
api_router.include_router(positions_router,   prefix="/positions",   tags=["positions"])
api_router.include_router(backtests_router,   prefix="/backtests",   tags=["backtests"])
api_router.include_router(connectors_router,  prefix="/connectors",  tags=["connectors"])
api_router.include_router(watchlist_router,   prefix="/watchlist",   tags=["watchlist"])
api_router.include_router(portfolio_router,   prefix="/portfolio",   tags=["portfolio"])
api_router.include_router(risk_router,        prefix="/risk",        tags=["risk"])
api_router.include_router(settings_router,    prefix="/settings",    tags=["settings"])
api_router.include_router(modules_router,     prefix="/modules",     tags=["modules"])
api_router.include_router(marketdata_router,  prefix="/marketdata",  tags=["marketdata"])
api_router.include_router(alerts_router,      prefix="/alerts",      tags=["alerts"])
api_router.include_router(logs_router,        prefix="/logs",        tags=["logs"])
api_router.include_router(ai_router,          prefix="/ai",          tags=["ai"])
api_router.include_router(webhooks_router,    prefix="/webhooks",    tags=["webhooks"])
api_router.include_router(indicators_router,  prefix="/indicators",  tags=["indicators"])
api_router.include_router(ws_router,          tags=["websockets"])
