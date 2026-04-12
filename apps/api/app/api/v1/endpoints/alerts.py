"""
Alerts API — alert management and notifications.
"""
from typing import List, Optional
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.models import Alert, AlertLevel

router = APIRouter()


class AlertCreate(BaseModel):
    title: str
    message: str
    level: str = "info"
    source: Optional[str] = None


@router.get("", response_model=List[dict], include_in_schema=False)
@router.get("/", response_model=List[dict])
async def list_alerts(
    unread_only: bool = False,
    level: Optional[str] = None,
    limit: int = 100,
    db: AsyncSession = Depends(get_db),
):
    q = select(Alert).order_by(Alert.created_at.desc()).limit(limit)
    if unread_only:
        q = q.where(not Alert.is_read)
    if level:
        try:
            q = q.where(Alert.level == AlertLevel(level))
        except ValueError:
            pass
    result = await db.execute(q)
    return [_a(a) for a in result.scalars().all()]


@router.get("/unread-count", response_model=dict)
async def unread_count(db: AsyncSession = Depends(get_db)):
    from sqlalchemy import func
    result = await db.execute(
        select(func.count(Alert.id)).where(not Alert.is_read)
    )
    return {"count": result.scalar() or 0}


@router.post("/", response_model=dict, status_code=201)
async def create_alert(data: AlertCreate, db: AsyncSession = Depends(get_db)):
    try:
        level = AlertLevel(data.level)
    except ValueError:
        level = AlertLevel.INFO

    alert = Alert(
        id=str(uuid.uuid4()),
        title=data.title,
        message=data.message,
        level=level,
        source=data.source,
        is_read=False,
    )
    db.add(alert)
    await db.commit()
    await db.refresh(alert)
    return _a(alert)


@router.post("/{alert_id}/read", response_model=dict)
async def mark_read(alert_id: str, db: AsyncSession = Depends(get_db)):
    a = await db.get(Alert, alert_id)
    if a:
        a.is_read = True
        await db.commit()
    return {"ok": True}


@router.post("/read-all", response_model=dict)
async def mark_all_read(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Alert).where(not Alert.is_read))
    count = 0
    for a in result.scalars().all():
        a.is_read = True
        count += 1
    await db.commit()
    return {"marked_read": count}


@router.delete("/{alert_id}", response_model=dict)
async def delete_alert(alert_id: str, db: AsyncSession = Depends(get_db)):
    a = await db.get(Alert, alert_id)
    if a:
        await db.delete(a)
        await db.commit()
    return {"deleted": True}


def _a(a: Alert) -> dict:
    return {
        "id":         a.id,
        "title":      a.title,
        "message":    a.message,
        "level":      a.level,
        "source":     a.source,
        "is_read":    a.is_read,
        "metadata":   a.extra_metadata,
        "created_at": a.created_at.isoformat() if a.created_at else None,
    }
