"""
Strategies API — CRUD for strategy definitions.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.models import Strategy, StrategyVersion
from app.strategy.dsl import StrategyDSL, SAMPLE_STRATEGIES

router = APIRouter()


class StrategyCreate(BaseModel):
    name: str
    description: Optional[str] = None
    market_type: str = "equity"
    dsl: dict
    tags: List[str] = []


class StrategyUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    dsl: Optional[dict] = None
    is_active: Optional[bool] = None
    tags: Optional[List[str]] = None


@router.get("/", response_model=List[dict])
async def list_strategies(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Strategy).order_by(Strategy.updated_at.desc()))
    return [_s(s) for s in result.scalars().all()]


@router.get("/samples", response_model=dict)
async def get_sample_strategies():
    """Return built-in sample strategies for quick-start."""
    return SAMPLE_STRATEGIES


@router.get("/{strategy_id}", response_model=dict)
async def get_strategy(strategy_id: str, db: AsyncSession = Depends(get_db)):
    s = await db.get(Strategy, strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    return _s(s)


@router.post("/", response_model=dict, status_code=201)
async def create_strategy(data: StrategyCreate, db: AsyncSession = Depends(get_db)):
    # Validate DSL
    try:
        StrategyDSL(**data.dsl)
    except Exception as e:
        raise HTTPException(status_code=422, detail=f"Invalid strategy DSL: {e}")

    strategy = Strategy(
        id=str(uuid.uuid4()),
        name=data.name,
        description=data.description,
        market_type=data.market_type,
        dsl=data.dsl,
        tags=data.tags,
        is_active=True,
    )
    db.add(strategy)

    # Create initial version
    version = StrategyVersion(
        id=str(uuid.uuid4()),
        strategy_id=strategy.id,
        version=1,
        dsl_snapshot=data.dsl,
        change_notes="Initial version",
    )
    db.add(version)
    await db.commit()
    await db.refresh(strategy)
    return _s(strategy)


@router.patch("/{strategy_id}", response_model=dict)
async def update_strategy(
    strategy_id: str, data: StrategyUpdate, db: AsyncSession = Depends(get_db)
):
    s = await db.get(Strategy, strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")

    if data.name is not None:
        s.name = data.name
    if data.description is not None:
        s.description = data.description
    if data.is_active is not None:
        s.is_active = data.is_active
    if data.tags is not None:
        s.tags = data.tags

    if data.dsl is not None:
        try:
            StrategyDSL(**data.dsl)
        except Exception as e:
            raise HTTPException(status_code=422, detail=f"Invalid DSL: {e}")
        s.dsl = data.dsl

        # Save a new version snapshot
        result = await db.execute(
            select(StrategyVersion)
            .where(StrategyVersion.strategy_id == strategy_id)
            .order_by(StrategyVersion.version.desc())
            .limit(1)
        )
        latest = result.scalar_one_or_none()
        next_ver = (latest.version + 1) if latest else 1
        db.add(StrategyVersion(
            id=str(uuid.uuid4()),
            strategy_id=strategy_id,
            version=next_ver,
            dsl_snapshot=data.dsl,
        ))

    await db.commit()
    await db.refresh(s)
    return _s(s)


@router.delete("/{strategy_id}")
async def delete_strategy(strategy_id: str, db: AsyncSession = Depends(get_db)):
    s = await db.get(Strategy, strategy_id)
    if not s:
        raise HTTPException(status_code=404, detail="Strategy not found")
    await db.delete(s)
    await db.commit()
    return {"deleted": True}


@router.get("/{strategy_id}/versions", response_model=List[dict])
async def get_versions(strategy_id: str, db: AsyncSession = Depends(get_db)):
    result = await db.execute(
        select(StrategyVersion)
        .where(StrategyVersion.strategy_id == strategy_id)
        .order_by(StrategyVersion.version.desc())
    )
    return [
        {"version": v.version, "created_at": v.created_at.isoformat(),
         "notes": v.change_notes, "dsl": v.dsl_snapshot}
        for v in result.scalars().all()
    ]


def _s(s: Strategy) -> dict:
    return {
        "id": s.id, "name": s.name, "description": s.description,
        "market_type": s.market_type, "dsl": s.dsl, "is_active": s.is_active,
        "tags": s.tags or [],
        "created_at": s.created_at.isoformat() if s.created_at else None,
        "updated_at": s.updated_at.isoformat() if s.updated_at else None,
    }
