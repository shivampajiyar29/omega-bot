"""Integration tests — require database connection."""
import pytest


@pytest.mark.integration
@pytest.mark.asyncio
async def test_api_health(client):
    r = await client.get("/health")
    assert r.status_code == 200
    data = r.json()
    assert data["status"] == "ok"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_strategies_list(client):
    r = await client.get("/api/v1/strategies/")
    assert r.status_code == 200
    assert isinstance(r.json(), list)


@pytest.mark.integration
@pytest.mark.asyncio
async def test_create_strategy(client):
    from app.strategy.dsl import SAMPLE_STRATEGIES
    payload = {
        "name": "Integration Test Strategy",
        "market_type": "equity",
        "dsl": SAMPLE_STRATEGIES.get("ema_crossover", {}),
    }
    r = await client.post("/api/v1/strategies/", json=payload)
    assert r.status_code == 201
    data = r.json()
    assert data["name"] == "Integration Test Strategy"


@pytest.mark.integration
@pytest.mark.asyncio
async def test_dashboard_summary(client):
    r = await client.get("/api/v1/dashboard/summary")
    assert r.status_code == 200


@pytest.mark.integration
@pytest.mark.asyncio
async def test_market_data_ohlcv(client):
    r = await client.get("/api/v1/marketdata/ohlcv?symbol=RELIANCE&exchange=NSE&timeframe=15m&limit=20")
    assert r.status_code == 200
    data = r.json()
    assert len(data) > 0
