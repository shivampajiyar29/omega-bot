"""
OmegaBot Trading Platform — FastAPI Application
Personal-use algorithmic trading platform.
"""
import asyncio
import logging
from contextlib import asynccontextmanager
from datetime import datetime, timezone
from typing import Any, Dict, Optional
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import settings
from app.core.database import AsyncSessionLocal, init_db
from app.core.logging import setup_logging
from app.api.v1.router import api_router

logger = logging.getLogger(__name__)


async def _check_db_once() -> Optional[str]:
    try:
        async with AsyncSessionLocal() as session:
            from sqlalchemy import text

            await session.execute(text("SELECT 1"))
        return None
    except Exception as exc:
        return f"{type(exc).__name__}: {exc}"


def _bool_configured(value: Optional[str]) -> bool:
    return bool(value and str(value).strip())


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: startup and shutdown."""
    setup_logging()
    app.state.started_at = datetime.now(timezone.utc).isoformat()
    app.state.startup_errors = []

    # Production-style startup: block until DB is reachable and tables created,
    # rather than "booting green" with a broken backend.
    try:
        await init_db()
        app.state.db_ready = True
    except Exception as exc:
        app.state.db_ready = False
        msg = f"DB init failed: {type(exc).__name__}: {exc}"
        app.state.startup_errors.append(msg)
        logger.exception(msg)
        raise

    # Redis-backed market stream is helpful but not required to boot API.
    # If Redis is misconfigured/offline, keep the API running and report degraded health.
    app.state.market_stream_task = None
    try:
        from app.services import market_stream

        await asyncio.to_thread(market_stream.seed_market_prices_if_empty)
        task = asyncio.create_task(market_stream.start_market_stream())
        app.state.market_stream_task = task
        app.state.redis_ready = True
    except Exception as exc:
        app.state.redis_ready = False
        msg = f"Market stream/Redis init failed: {type(exc).__name__}: {exc}"
        app.state.startup_errors.append(msg)
        logger.exception(msg)

    yield
    task = getattr(app.state, "market_stream_task", None)
    if task is not None:
        task.cancel()
        try:
            await task
        except asyncio.CancelledError:
            pass


def create_app() -> FastAPI:
    app = FastAPI(
        title=settings.APP_NAME,
        description="Personal Algorithmic Trading Platform",
        version="1.0.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    # ─── Middleware ───────────────────────────────────────────────────────────
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.add_middleware(GZipMiddleware, minimum_size=1000)

    # ─── Routers ─────────────────────────────────────────────────────────────
    app.include_router(api_router, prefix="/api/v1")

    # ─── Health ──────────────────────────────────────────────────────────────
    @app.get("/health", tags=["health"])
    async def health_check():
        return {"status": "ok", "app": settings.APP_NAME}

    @app.get("/api/health", tags=["health"])
    async def api_health_check():
        db_err = await _check_db_once()
        db_ok = db_err is None

        redis_ok = bool(getattr(app.state, "redis_ready", False))
        startup_errors = list(getattr(app.state, "startup_errors", []))

        status = "ok" if db_ok else "degraded"
        return {
            "status": status,
            "app": settings.APP_NAME,
            "env": settings.APP_ENV,
            "started_at": getattr(app.state, "started_at", None),
            "components": {
                "db": {"ok": db_ok, "error": db_err},
                "redis": {"ok": redis_ok},
                "ai": {"enabled": bool(settings.ai_enabled)},
            },
            "startup_errors": startup_errors,
        }

    @app.get("/api/config/status", tags=["config"])
    async def config_status() -> Dict[str, Any]:
        """
        Config visibility endpoint for the frontend Settings UI.
        Never returns secret values; only "configured" flags and friendly messages.
        """
        default_provider = (settings.DEFAULT_AI_PROVIDER or "").strip().lower()
        fallback_enabled = bool(settings.ENABLE_AI_FALLBACK)

        providers = {
            "openai": {"configured": _bool_configured(settings.OPENAI_API_KEY)},
            "anthropic": {"configured": _bool_configured(settings.ANTHROPIC_API_KEY)},
            "perplexity": {"configured": _bool_configured(settings.PERPLEXITY_API_KEY)},
        }

        enabled_any = any(p["configured"] for p in providers.values())
        active_configured = providers.get(default_provider, {}).get("configured", False)

        messages = []
        if not enabled_any:
            messages.append("No AI provider keys configured. AI Assistant will be unavailable until a key is set.")
        elif not active_configured:
            messages.append(f"Default AI provider '{default_provider}' is not configured; fallback may be used if enabled.")
        if not fallback_enabled and enabled_any and not active_configured:
            messages.append("AI fallback is disabled, so AI requests may fail when the default provider is unavailable.")

        return {
            "backend": {
                "online": True,
                "app": settings.APP_NAME,
                "env": settings.APP_ENV,
                "started_at": getattr(app.state, "started_at", None),
            },
            "db": {"url_driver": str(settings.DATABASE_URL).split(':', 1)[0], "ready": bool(getattr(app.state, "db_ready", False))},
            "cors": {"origins": settings.CORS_ORIGINS},
            "ai": {
                "default_provider": default_provider,
                "fallback_enabled": fallback_enabled,
                "providers": providers,
            },
            "messages": messages,
        }

    return app


app = create_app()
