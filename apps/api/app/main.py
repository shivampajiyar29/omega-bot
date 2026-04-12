"""
OmegaBot Trading Platform — FastAPI Application
Personal-use algorithmic trading platform.
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
    """Application lifespan: startup → serve → shutdown."""
    setup_logging()
    app.state.started_at = datetime.now(timezone.utc).isoformat()
    app.state.startup_errors = []

    # ── Database ──────────────────────────────────────────────────────────────
    try:
        await init_db()
        app.state.db_ready = True
        logger.info("✓ Database ready")
    except Exception as exc:
        app.state.db_ready = False
        msg = f"DB init failed: {exc}"
        app.state.startup_errors.append(msg)
        logger.error(msg)
        raise   # fail fast — no point serving if DB is down

    # ── Redis / market stream (non-fatal) ─────────────────────────────────────
    app.state.market_stream_task = None
    try:
        from app.services import market_stream
        await asyncio.to_thread(market_stream.seed_market_prices_if_empty)
        task = asyncio.create_task(market_stream.start_market_stream())
        app.state.market_stream_task = task
        app.state.redis_ready = True
        logger.info("✓ Market stream running")
    except Exception as exc:
        app.state.redis_ready = False
        msg = f"Market stream/Redis unavailable: {exc}"
        app.state.startup_errors.append(msg)
        logger.warning(f"⚠ {msg} — continuing without Redis")

    yield   # ── Serving ──────────────────────────────────────────────────────

    # Cleanup
    task = getattr(app.state, "market_stream_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass
    logger.info("OmegaBot shutdown complete")


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Personal Algorithmic Trading Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        redirect_slashes=False,   # prevent 307 redirects on missing trailing slash
        lifespan=lifespan,
    )

    # ── Middleware ────────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ── Routes ────────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ── Health endpoints ──────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health():
        return {"status": "ok", "app": settings.APP_NAME, "version": "1.0.0"}

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
            "app": settings.APP_NAME,
            "started_at": getattr(app.state, "started_at", None),
            "components": {
                "db":    {"ok": db_ok},
                "redis": {"ok": bool(getattr(app.state, "redis_ready", False))},
                "ai":    {"enabled": settings.ai_enabled},
            },
            "startup_errors": getattr(app.state, "startup_errors", []),
        }

    @app.get("/api/config/status", tags=["config"])
    async def config_status() -> Dict[str, Any]:
        providers = {
            "openai":      {"configured": bool(settings.OPENAI_API_KEY)},
            "anthropic":   {"configured": bool(settings.ANTHROPIC_API_KEY)},
            "gemini":      {"configured": bool(settings.GEMINI_API_KEY)},
            "nvidia":      {"configured": bool(settings.NVIDIA_API_KEY)},
            "openrouter":  {"configured": bool(settings.OPENROUTER_API_KEY)},
        }
        return {
            "backend":  {"online": True, "app": settings.APP_NAME},
            "db":       {"ready": bool(getattr(app.state, "db_ready", False))},
            "ai":       {"providers": providers, "any_configured": settings.ai_enabled},
        }

    return app


app = create_app()
