"""
Database connection setup — async SQLAlchemy with PostgreSQL.
"""
import asyncio
import logging
from typing import AsyncGenerator

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.models.models import Base

logger = logging.getLogger(__name__)

engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
    poolclass=NullPool,
)

AsyncSessionLocal = async_sessionmaker(
    engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)


async def init_db(max_retries: int = 8, retry_delay_seconds: float = 2.0):
    """Ensure DB connection works and create tables if missing."""
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))

            failed_tables: list[str] = []
            for table in Base.metadata.sorted_tables:
                try:
                    async with engine.begin() as conn:
                        await conn.run_sync(lambda sync_conn, t=table: t.create(sync_conn, checkfirst=True))
                except Exception:
                    failed_tables.append(table.name)
                    logger.exception("Table init failed for '%s'.", table.name)

            if failed_tables:
                logger.warning(
                    "Some tables failed during startup init: %s",
                    sorted(failed_tables),
                )
            logger.info("Database initialization completed successfully.")
            return
        except Exception as exc:  # pragma: no cover - startup path
            last_error = exc
            logger.exception(
                "Database initialization failed (attempt %s/%s).",
                attempt,
                max_retries,
            )
            if attempt < max_retries:
                await asyncio.sleep(retry_delay_seconds)

    raise RuntimeError("Database initialization failed after retries.") from last_error


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
