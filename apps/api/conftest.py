"""
Pytest configuration — shared fixtures for all tests.
Uses SQLite so no PostgreSQL needed for running tests.
"""
import asyncio
import os
import pytest

# Override env before any app imports
os.environ.setdefault("DATABASE_URL", "sqlite+aiosqlite:///./test_omegabot.db")
os.environ.setdefault("REDIS_URL",    "redis://localhost:6379/15")
os.environ.setdefault("SECRET_KEY",   "test-secret-key-not-for-production")
os.environ.setdefault("APP_ENV",      "test")


@pytest.fixture(scope="session")
def event_loop():
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


@pytest.fixture(scope="session", autouse=True)
async def setup_test_db():
    """Create tables once for the entire test session."""
    from app.core.database import engine, Base
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    yield
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.drop_all)
    await engine.dispose()
    # Cleanup test DB file
    if os.path.exists("test_omegabot.db"):
        os.remove("test_omegabot.db")


@pytest.fixture
async def db_session():
    """Provide a clean DB session per test."""
    from app.core.database import AsyncSessionLocal
    async with AsyncSessionLocal() as session:
        yield session
        await session.rollback()


@pytest.fixture
def app():
    from app.main import create_app
    return create_app()


@pytest.fixture
async def client(app):
    from httpx import AsyncClient, ASGITransport
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
async def mock_broker():
    from app.adapters.broker.mock_broker import MockBrokerAdapter
    b = MockBrokerAdapter(config={"initial_capital": 100_000})
    await b.connect()
    b.update_price("RELIANCE", 2800.0)
    b.update_price("TCS", 3900.0)
    b.update_price("BTCUSDT", 87000.0)
    yield b
    await b.disconnect()
