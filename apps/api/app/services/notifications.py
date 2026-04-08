"""
Notifications service — sends alerts via Telegram (and future channels).
All notification calls are fire-and-forget async.
"""
import asyncio
import logging
from typing import Optional
from app.core.config import settings

logger = logging.getLogger(__name__)


class NotificationService:
    """
    Sends notifications through configured channels.
    Currently supports Telegram. Easily extensible.
    """

    def __init__(self):
        self._telegram_enabled = bool(settings.TELEGRAM_BOT_TOKEN and settings.TELEGRAM_CHAT_ID)

    async def notify(
        self,
        message: str,
        level: str = "info",    # info | warning | error | critical
        title: Optional[str] = None,
    ):
        """Send a notification through all enabled channels."""
        tasks = []
        if self._telegram_enabled:
            tasks.append(self._send_telegram(message, level, title))
        if tasks:
            await asyncio.gather(*tasks, return_exceptions=True)

    async def notify_order_filled(self, symbol: str, side: str, qty: float, price: float, pnl: Optional[float] = None):
        icon = "🟢" if side == "buy" else "🔴"
        msg = f"{icon} {side.upper()} {qty} {symbol} @ ₹{price:,.2f}"
        if pnl is not None:
            msg += f" | P&L: {'▲' if pnl >= 0 else '▼'} ₹{abs(pnl):,.0f}"
        await self.notify(msg, level="info", title="Order Filled")

    async def notify_risk_event(self, event_type: str, message: str):
        await self.notify(f"⚠️ {event_type}: {message}", level="warning", title="Risk Alert")

    async def notify_kill_switch(self, bots_stopped: int):
        await self.notify(
            f"🛑 Kill switch activated — {bots_stopped} bot(s) stopped.",
            level="critical", title="Kill Switch"
        )

    async def notify_backtest_complete(self, name: str, win_rate: float, total_return: float):
        icon = "📈" if total_return >= 0 else "📉"
        await self.notify(
            f"{icon} Backtest complete: {name}\nReturn: {total_return:+.1f}% | Win rate: {win_rate:.1f}%",
            level="info", title="Backtest Done"
        )

    async def _send_telegram(self, message: str, level: str, title: Optional[str] = None):
        try:
            import httpx
            prefix = {"info": "ℹ️", "warning": "⚠️", "error": "❌", "critical": "🚨"}.get(level, "")
            full_msg = f"{prefix} *{title}*\n{message}" if title else f"{prefix} {message}"
            url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
            async with httpx.AsyncClient(timeout=5.0) as client:
                await client.post(url, json={
                    "chat_id": settings.TELEGRAM_CHAT_ID,
                    "text": full_msg,
                    "parse_mode": "Markdown",
                })
        except Exception as e:
            logger.error(f"Telegram notification failed: {e}")


# Singleton instance
notifications = NotificationService()
