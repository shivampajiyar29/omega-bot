"""
Strategy Service — business logic for strategy management.
Keeps API endpoints thin by centralising complex operations here.
"""
from __future__ import annotations
import uuid
from typing import List, Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.models import Strategy, StrategyVersion
from app.strategy.dsl import StrategyDSL, SAMPLE_STRATEGIES


class StrategyService:

    def __init__(self, db: AsyncSession):
        self.db = db

    async def create(
        self,
        name: str,
        dsl: Dict[str, Any],
        description: str = "",
        market_type: str = "equity",
        tags: List[str] = None,
    ) -> Strategy:
        """Create a strategy and its initial version snapshot."""
        # Validate DSL
        StrategyDSL(**dsl)

        strategy = Strategy(
            id=str(uuid.uuid4()),
            name=name,
            description=description,
            market_type=market_type,
            dsl=dsl,
            tags=tags or [],
            is_active=True,
        )
        self.db.add(strategy)

        version = StrategyVersion(
            id=str(uuid.uuid4()),
            strategy_id=strategy.id,
            version=1,
            dsl_snapshot=dsl,
            change_notes="Initial version",
        )
        self.db.add(version)
        await self.db.flush()
        return strategy

    async def update(
        self,
        strategy_id: str,
        name: Optional[str] = None,
        dsl: Optional[Dict[str, Any]] = None,
        description: Optional[str] = None,
        is_active: Optional[bool] = None,
        tags: Optional[List[str]] = None,
        change_notes: str = "",
    ) -> Optional[Strategy]:
        s = await self.db.get(Strategy, strategy_id)
        if not s:
            return None

        if name is not None:
            s.name = name
        if description is not None:
            s.description = description
        if is_active is not None:
            s.is_active = is_active
        if tags is not None:
            s.tags = tags

        if dsl is not None:
            StrategyDSL(**dsl)  # validate
            s.dsl = dsl
            # Create new version
            latest = await self._latest_version(strategy_id)
            version = StrategyVersion(
                id=str(uuid.uuid4()),
                strategy_id=strategy_id,
                version=(latest + 1) if latest else 2,
                dsl_snapshot=dsl,
                change_notes=change_notes,
            )
            self.db.add(version)

        await self.db.flush()
        return s

    async def delete(self, strategy_id: str) -> bool:
        s = await self.db.get(Strategy, strategy_id)
        if not s:
            return False
        # Check if any running bots use this strategy
        from app.models.models import Bot, BotStatus
        result = await self.db.execute(
            select(Bot).where(Bot.strategy_id == strategy_id, Bot.status == BotStatus.RUNNING)
        )
        running_bots = result.scalars().all()
        if running_bots:
            raise ValueError(
                f"Cannot delete strategy with {len(running_bots)} running bot(s). Stop them first."
            )
        await self.db.delete(s)
        await self.db.flush()
        return True

    async def get(self, strategy_id: str) -> Optional[Strategy]:
        return await self.db.get(Strategy, strategy_id)

    async def list_all(self, active_only: bool = False) -> List[Strategy]:
        q = select(Strategy).order_by(Strategy.updated_at.desc())
        if active_only:
            q = q.where(Strategy.is_active)
        result = await self.db.execute(q)
        return result.scalars().all()

    async def get_versions(self, strategy_id: str) -> List[StrategyVersion]:
        result = await self.db.execute(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyVersion.version.desc())
        )
        return result.scalars().all()

    async def restore_version(self, strategy_id: str, version_num: int) -> Optional[Strategy]:
        """Restore a strategy to a previous version."""
        result = await self.db.execute(
            select(StrategyVersion).where(
                StrategyVersion.strategy_id == strategy_id,
                StrategyVersion.version == version_num,
            )
        )
        version = result.scalar_one_or_none()
        if not version:
            return None
        return await self.update(
            strategy_id=strategy_id,
            dsl=version.dsl_snapshot,
            change_notes=f"Restored to version {version_num}",
        )

    async def load_samples(self) -> int:
        """Load built-in sample strategies if they don't already exist."""
        loaded = 0
        for key, dsl in SAMPLE_STRATEGIES.items():
            result = await self.db.execute(
                select(Strategy).where(Strategy.name == dsl["name"])
            )
            if not result.scalar_one_or_none():
                await self.create(
                    name=dsl["name"],
                    dsl=dsl,
                    description=dsl.get("description", ""),
                    market_type=dsl.get("market_types", ["equity"])[0],
                    tags=["sample", key],
                )
                loaded += 1
        return loaded

    async def _latest_version(self, strategy_id: str) -> int:
        result = await self.db.execute(
            select(StrategyVersion.version)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyVersion.version.desc())
            .limit(1)
        )
        v = result.scalar_one_or_none()
        return v or 1
