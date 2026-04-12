"""
Bot Manager — manages lifecycle of all running strategy bots.
"""
from __future__ import annotations
import asyncio
import logging
from typing import Dict, List, Optional

logger = logging.getLogger(__name__)


class BotManager:
    def __init__(self):
        self._bots: Dict[str, Dict] = {}
        self._tasks: Dict[str, asyncio.Task] = {}
        self._lock = asyncio.Lock()

    async def start_bot(self, bot_id: str, bot_name: str, strategy_dsl: dict,
                        symbol: str, exchange: str, connector_name: str = "mock",
                        broker_config: dict = None, risk_config: dict = None,
                        trading_mode: str = "paper") -> Dict:
        async with self._lock:
            if bot_id in self._bots and self._bots[bot_id].get("status") == "running":
                return self._bots[bot_id]

            self._bots[bot_id] = {
                "id": bot_id, "name": bot_name, "symbol": symbol,
                "exchange": exchange, "status": "running",
                "signals": 0, "trades": 0, "pnl": 0.0,
            }
            logger.info(f"Bot {bot_name} started for {symbol}")
            return self._bots[bot_id]

    async def stop_bot(self, bot_id: str) -> bool:
        async with self._lock:
            if bot_id in self._bots:
                self._bots[bot_id]["status"] = "stopped"
                task = self._tasks.pop(bot_id, None)
                if task:
                    task.cancel()
                return True
            return False

    def pause_bot(self, bot_id: str) -> bool:
        if bot_id in self._bots:
            self._bots[bot_id]["status"] = "paused"
            return True
        return False

    def resume_bot(self, bot_id: str) -> bool:
        if bot_id in self._bots:
            self._bots[bot_id]["status"] = "running"
            return True
        return False

    async def stop_all(self) -> int:
        bot_ids = list(self._bots.keys())
        for bid in bot_ids:
            await self.stop_bot(bid)
        logger.warning(f"Kill switch: stopped {len(bot_ids)} bots")
        return len(bot_ids)

    def get_status(self, bot_id: str) -> Optional[Dict]:
        return self._bots.get(bot_id)

    def get_all_statuses(self) -> List[Dict]:
        return list(self._bots.values())

    @property
    def active_count(self) -> int:
        return sum(1 for b in self._bots.values() if b.get("status") == "running")


bot_manager = BotManager()
