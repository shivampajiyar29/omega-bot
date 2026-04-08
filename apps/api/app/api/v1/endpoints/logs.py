"""
Logs & Audit API — system event log.
"""
from typing import List, Optional
from datetime import datetime
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
import uuid

from app.core.database import get_db
from app.models.models import AuditLog

router = APIRouter()


class LogCreate(BaseModel):
    action: str
    entity_type: Optional[str] = None
    entity_id: Optional[str] = None
    details: Optional[dict] = None


@router.get("/", response_model=List[dict])
async def list_logs(
    action: Optional[str] = None,
    entity_type: Optional[str] = None,
    limit: int = 200,
    db: AsyncSession = Depends(get_db),
):
    q = select(AuditLog).order_by(AuditLog.logged_at.desc()).limit(limit)
    if action:
        q = q.where(AuditLog.action.contains(action))
    if entity_type:
        q = q.where(AuditLog.entity_type == entity_type)
    result = await db.execute(q)
    return [_l(l) for l in result.scalars().all()]


@router.post("/", response_model=dict, status_code=201)
async def write_log(data: LogCreate, db: AsyncSession = Depends(get_db)):
    """Internal endpoint for writing audit log entries."""
    log = AuditLog(
        id=str(uuid.uuid4()),
        action=data.action,
        entity_type=data.entity_type,
        entity_id=data.entity_id,
        details=data.details,
        logged_at=datetime.utcnow(),
    )
    db.add(log)
    await db.commit()
    return {"id": log.id, "logged": True}


@router.delete("/clear", response_model=dict)
async def clear_old_logs(days_old: int = 30, db: AsyncSession = Depends(get_db)):
    """Delete log entries older than N days."""
    from datetime import timedelta
    cutoff = datetime.utcnow() - timedelta(days=days_old)
    result = await db.execute(select(AuditLog).where(AuditLog.logged_at < cutoff))
    logs = result.scalars().all()
    count = len(logs)
    for log in logs:
        await db.delete(log)
    await db.commit()
    return {"deleted": count, "cutoff_days": days_old}


def _l(l: AuditLog) -> dict:
    return {
        "id":          l.id,
        "action":      l.action,
        "entity_type": l.entity_type,
        "entity_id":   l.entity_id,
        "details":     l.details,
        "ip_address":  l.ip_address,
        "logged_at":   l.logged_at.isoformat() if l.logged_at else None,
    }
