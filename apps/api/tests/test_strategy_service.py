"""
Tests for the StrategyService business logic layer.
"""
import pytest
from app.strategy.dsl import SAMPLE_STRATEGIES


class TestStrategyService:
    """Tests for StrategyService — uses conftest.py's db_session fixture."""

    @pytest.mark.asyncio
    async def test_create_strategy(self, db_session):
        from app.services.strategy_service import StrategyService
        svc = StrategyService(db_session)

        strategy = await svc.create(
            name="Test EMA Strategy",
            dsl=SAMPLE_STRATEGIES["ema_crossover"],
            description="Test strategy",
            market_type="equity",
            tags=["test"],
        )
        await db_session.flush()

        assert strategy.id
        assert strategy.name == "Test EMA Strategy"
        assert strategy.is_active is True
        assert "test" in strategy.tags

    @pytest.mark.asyncio
    async def test_create_invalid_dsl_raises(self, db_session):
        from app.services.strategy_service import StrategyService
        svc = StrategyService(db_session)

        with pytest.raises(Exception):  # pydantic ValidationError
            await svc.create(
                name="Bad Strategy",
                dsl={"name": "bad", "entry": "not_valid"},
            )

    @pytest.mark.asyncio
    async def test_update_strategy(self, db_session):
        from app.services.strategy_service import StrategyService
        svc = StrategyService(db_session)

        s = await svc.create("Original", SAMPLE_STRATEGIES["ema_crossover"])
        await db_session.flush()

        updated = await svc.update(s.id, name="Updated Name")
        assert updated.name == "Updated Name"

    @pytest.mark.asyncio
    async def test_update_dsl_creates_version(self, db_session):
        from app.services.strategy_service import StrategyService
        from app.models.models import StrategyVersion
        from sqlalchemy import select
        svc = StrategyService(db_session)

        s = await svc.create("Versioned", SAMPLE_STRATEGIES["ema_crossover"])
        await db_session.flush()

        new_dsl = dict(SAMPLE_STRATEGIES["rsi_breakout"])
        await svc.update(s.id, dsl=new_dsl, change_notes="Switched to RSI")
        await db_session.flush()

        result = await db_session.execute(
            select(StrategyVersion).where(StrategyVersion.strategy_id == s.id)
        )
        versions = result.scalars().all()
        assert len(versions) == 2  # initial + update

    @pytest.mark.asyncio
    async def test_delete_strategy(self, db_session):
        from app.services.strategy_service import StrategyService
        svc = StrategyService(db_session)

        s = await svc.create("To Delete", SAMPLE_STRATEGIES["ema_crossover"])
        await db_session.flush()

        deleted = await svc.delete(s.id)
        assert deleted is True

        retrieved = await svc.get(s.id)
        assert retrieved is None

    @pytest.mark.asyncio
    async def test_load_samples(self, db_session):
        from app.services.strategy_service import StrategyService
        svc = StrategyService(db_session)

        count = await svc.load_samples()
        assert count > 0

        # Running again should not duplicate
        count2 = await svc.load_samples()
        assert count2 == 0

    @pytest.mark.asyncio
    async def test_get_versions(self, db_session):
        from app.services.strategy_service import StrategyService
        svc = StrategyService(db_session)

        s = await svc.create("With Versions", SAMPLE_STRATEGIES["ema_crossover"])
        await db_session.flush()

        versions = await svc.get_versions(s.id)
        assert len(versions) == 1
        assert versions[0].version == 1
