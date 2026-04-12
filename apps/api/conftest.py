"""
Pytest configuration — shared fixtures.
Uses SQLite so no PostgreSQL needed for unit tests.
"""
import asyncio
import os
import pytest

# Set env before any imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_omegabot.db")
os.environ.setdefault("REDIS_URL", "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY", "test-secret-key-not-for-production")
os.environ.setdefault("APP_ENV", "test")

# Configure pytest-asyncio
def pytest_configure(config):
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "slow: marks tests as slow")


@pytest.fixture(scope="session")
def event_loop_policy():
    return asyncio.DefaultEventLoopPolicy()


@pytest.fixture
def app():
    from app.main import create_app
    return create_app()


@pytest.fixture
async def client(app):
    from httpx import AsyncClient, ASGITransport
    # Setup DB for integration tests
    from app.core.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    if os.path.exists("test_omegabot.db"):
        os.remove("test_omegabot.db")


@pytest.fixture
async def db_session():
    from app.core.database import AsyncSessionLocal, engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()
