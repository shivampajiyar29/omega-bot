"""
Risk Guard — pre-execution risk validation.
"""
from __future__ import annotations
import logging
from datetime import datetime, date
from typing import Dict, List

logger = logging.getLogger(__name__)


class RiskGuard:
    def __init__(self, config: Dict):
        self.config = config
        self._daily_loss: float = 0.0
        self._daily_trades: int = 0
        self._last_reset: date = date.today()
        self._open_positions: int = 0

    def validate_order(self, symbol: str, side: str, quantity: float,
                       price: float, current_positions: int = 0) -> List[str]:
        self._maybe_reset_daily()
        violations = []

        order_value = quantity * price
        max_val = self.config.get("max_order_value", 50000)
        if order_value > max_val:
            violations.append(f"Order value ₹{order_value:,.0f} exceeds max ₹{max_val:,.0f}")

        max_daily = self.config.get("max_daily_loss", 5000)
        if abs(self._daily_loss) >= max_daily:
            violations.append(f"Daily loss limit ₹{max_daily:,.0f} reached")

        max_pos = self.config.get("max_open_positions", 10)
        if side == "buy" and current_positions >= max_pos:
            violations.append(f"Max open positions ({max_pos}) reached")

        blacklist = [s.upper() for s in self.config.get("symbol_blacklist", [])]
        if symbol.upper() in blacklist:
            violations.append(f"{symbol} is blacklisted")

        start = self.config.get("allowed_hours_start")
        end = self.config.get("allowed_hours_end")
        if start and end:
            now = datetime.now().strftime("%H:%M")
            if not (start <= now <= end):
                violations.append(f"Outside trading hours ({start}–{end})")

        if violations:
            logger.warning(f"RiskGuard blocked {side} {quantity} {symbol}: {'; '.join(violations)}")
        return violations

    def record_fill(self, pnl: float):
        self._daily_loss += pnl
        self._daily_trades += 1

    def get_daily_stats(self) -> Dict:
        return {
            "daily_pnl": round(self._daily_loss, 2),
            "daily_trades": self._daily_trades,
            "open_positions": self._open_positions,
            "date": self._last_reset.isoformat(),
        }

    def _maybe_reset_daily(self):
        today = date.today()
        if today != self._last_reset:
            self._daily_loss = 0.0
            self._daily_trades = 0
            self._last_reset = today
            logger.info("RiskGuard: daily counters reset")
