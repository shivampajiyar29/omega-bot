"""Trade Journal API — in-memory store with optional DB persistence."""
from typing import Dict, List, Optional
from datetime import datetime
from fastapi import APIRouter
from pydantic import BaseModel

router = APIRouter()

_DEMO: List[Dict] = [
    {
        "id": "demo-1",
        "symbol": "RELIANCE",
        "side": "long",
        "entry_price": 2831.0,
        "exit_price": 2847.3,
        "quantity": 50,
        "pnl": 815.0,
        "setup": "EMA crossover on 15m",
        "notes": "Clean breakout with volume confirmation",
        "tags": ["trend", "momentum"],
        "rating": 4,
        "timeframe": "15m",
        "strategy_name": "EMA Crossover",
        "entry_time": "2024-01-15T09:45:00",
        "created_at": "2024-01-15T12:31:00",
    },
]


class JournalCreate(BaseModel):
    symbol: str
    side: str = "long"
    entry_price: float
    quantity: float = 1.0
    exit_price: Optional[float] = None
    pnl: Optional[float] = None
    setup: str = ""
    notes: str = ""
    tags: List[str] = []
    rating: int = 3
    timeframe: str = "15m"
    strategy_name: Optional[str] = None


@router.get("/")
async def list_journal(symbol: Optional[str] = None, limit: int = 50):
    data = _DEMO[:]
    if symbol:
        data = [e for e in data if e.get("symbol", "").upper() == symbol.upper()]
    return data[:limit]


@router.post("/", status_code=201)
async def create_entry(data: JournalCreate):
    import uuid
    entry = data.model_dump()
    entry["id"] = str(uuid.uuid4())[:8]
    entry["created_at"] = datetime.utcnow().isoformat()
    if entry.get("exit_price") and entry.get("entry_price"):
        mult = 1 if entry["side"] == "long" else -1
        entry["pnl"] = round(
            (entry["exit_price"] - entry["entry_price"]) * entry["quantity"] * mult, 2
        )
    _DEMO.insert(0, entry)
    return entry


@router.delete("/{entry_id}")
async def delete_entry(entry_id: str):
    global _DEMO
    _DEMO = [e for e in _DEMO if e.get("id") != entry_id]
    return {"deleted": True}


@router.get("/stats/summary")
async def stats():
    if not _DEMO:
        return {"total": 0}
    pnls = [e.get("pnl") or 0 for e in _DEMO]
    wins = [p for p in pnls if p > 0]
    losses = [p for p in pnls if p < 0]
    return {
        "total": len(_DEMO),
        "total_pnl": round(sum(pnls), 2),
        "win_count": len(wins),
        "loss_count": len(losses),
        "win_rate_pct": round(len(wins) / len(_DEMO) * 100, 1) if _DEMO else 0,
        "avg_win": round(sum(wins) / len(wins), 2) if wins else 0,
        "avg_loss": round(sum(losses) / len(losses), 2) if losses else 0,
    }
