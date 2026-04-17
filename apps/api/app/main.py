"""
OmegaBot Trading Platform — FastAPI Application
Real-time paper trading + AI signals + live market data
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.database import init_db
from app.core.logging import setup_logging
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Startup: init DB → seed prices → start market stream + paper trading loop."""
    setup_logging()
    app.state.started_at     = datetime.now(timezone.utc).isoformat()
    app.state.startup_errors = []

    # ── 1. Database ──────────────────────────────────────────────────────────
    try:
        await init_db()
        app.state.db_ready = True
        logger.info("✅ Database ready")
    except Exception as exc:
        app.state.db_ready = False
        msg = f"DB init failed: {exc}"
        app.state.startup_errors.append(msg)
        logger.error(msg)
        raise

    # ── 2. Market stream (Redis + Binance) ───────────────────────────────────
    app.state.market_stream_task = None
    try:
        from app.services import market_stream
        await asyncio.to_thread(market_stream.seed_market_prices_if_empty)
        task = asyncio.create_task(market_stream.start_market_stream())
        app.state.market_stream_task = task
        app.state.redis_ready = True
        logger.info("✅ Market stream running (Binance crypto + simulated Indian)")
    except Exception as exc:
        app.state.redis_ready = False
        msg = f"Market stream failed: {exc}"
        app.state.startup_errors.append(msg)
        logger.warning("⚠ %s — continuing without Redis", msg)

    # ── 3. Paper trading loop ────────────────────────────────────────────────
    app.state.paper_trading_task = None
    try:
        task = asyncio.create_task(_paper_trading_loop())
        app.state.paper_trading_task = task
        logger.info("✅ Paper trading loop started")
    except Exception as exc:
        logger.warning("⚠ Paper trading loop failed to start: %s", exc)

    yield  # ── Serving ──────────────────────────────────────────────────────

    # Cleanup
    for attr in ("market_stream_task", "paper_trading_task"):
        task = getattr(app.state, attr, None)
        if task:
            task.cancel()
            try:
                await task
            except asyncio.CancelledError:
                pass
    logger.info("OmegaBot shutdown complete")


async def _paper_trading_loop() -> None:
    """
    Background loop: every 15 seconds, execute pending AI signals as paper trades
    and mark all open positions to market.
    """
    from app.services.paper_trading import execute_pending_signals_async, mark_to_market_all
    while True:
        try:
            await execute_pending_signals_async()
            await mark_to_market_all()
        except asyncio.CancelledError:
            break
        except Exception as e:
            logger.error("Paper trading loop error: %s", e)
        await asyncio.sleep(15)


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Personal Algorithmic Trading Platform — Real paper trading with AI signals",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        redirect_slashes=False,
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    app.include_router(api_router, prefix="/api/v1")

    @app.get("/health", tags=["health"])
    async def health():
        return {
            "status": "ok",
            "app": settings.APP_NAME,
            "version": "1.0.0",
            "db_ready": bool(getattr(app.state, "db_ready", False)),
            "redis_ready": bool(getattr(app.state, "redis_ready", False)),
            "started_at": getattr(app.state, "started_at", None),
        }

    @app.get("/api/health", tags=["health"])
    async def api_health():
        from app.core.database import AsyncSessionLocal
        from sqlalchemy import text
        db_ok = False
        try:
            async with AsyncSessionLocal() as s:
                await s.execute(text("SELECT 1"))
            db_ok = True
        except Exception:
            pass
        return {
            "status": "ok" if db_ok else "degraded",
            "components": {
                "db":             {"ok": db_ok},
                "redis":          {"ok": bool(getattr(app.state, "redis_ready", False))},
                "market_stream":  {"running": getattr(app.state, "market_stream_task") is not None},
                "paper_trading":  {"running": getattr(app.state, "paper_trading_task") is not None},
                "ai":             {"provider": settings.AI_PROVIDER,
                                   "gemini_configured": bool(settings.GEMINI_API_KEY)},
            },
            "startup_errors": getattr(app.state, "startup_errors", []),
        }

    @app.get("/api/config/status", tags=["config"])
    async def config_status() -> Dict[str, Any]:
        return {
            "backend":  {"online": True, "app": settings.APP_NAME},
            "db":       {"ready": bool(getattr(app.state, "db_ready", False))},
            "ai":       {
                "provider": settings.AI_PROVIDER,
                "gemini":   {"configured": bool(settings.GEMINI_API_KEY)},
                "nvidia":   {"configured": bool(settings.NVIDIA_API_KEY)},
            },
            "brokers": {
                "binance":  {"configured": bool(settings.BINANCE_API_KEY)},
                "groww":    {"configured": bool(settings.GROWW_ACCESS_TOKEN)},
            },
        }

    return app


app = create_app()
