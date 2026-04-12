"""
Execution Engine — routes signals to broker adapters with risk checks.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, Optional

from app.adapters.broker.mock_broker import MockBrokerAdapter

logger = logging.getLogger(__name__)


class RiskCheckFailed(Exception):
    pass


class ExecutionEngine:
    def __init__(self, broker_name: str = "mock", broker_config: Dict = None, risk_config: Dict = None):
        self.broker_name = broker_name
        self._daily_pnl: float = 0.0
        self._prices: Dict[str, float] = {}
        self.risk_config = risk_config or {
            "max_daily_loss": 5000.0,
            "max_order_value": 50000.0,
            "max_open_positions": 10,
            "symbol_blacklist": [],
            "allowed_hours_start": None,
            "allowed_hours_end": None,
        }

        cfg = broker_config or {}
        self.broker = MockBrokerAdapter(config=cfg)
        self._connected = False

    async def start(self):
        await self.broker.connect()
        self._connected = True
        logger.info(f"ExecutionEngine started with broker: {self.broker_name}")

    async def stop(self):
        await self.broker.disconnect()
        self._connected = False

    def update_price(self, symbol: str, price: float):
        self._prices[symbol] = price
        if hasattr(self.broker, 'update_price'):
            self.broker.update_price(symbol, price)

    async def submit_order(self, symbol: str, side: str, order_type: str,
                           quantity: float, price: Optional[float] = None,
                           exchange: str = "NSE", bot_id: Optional[str] = None,
                           **kwargs) -> Dict[str, Any]:
        if not self._connected:
            raise RuntimeError("ExecutionEngine not started")

        # Risk checks
        current_price = price or self._prices.get(symbol, 0)
        order_value = quantity * current_price
        if order_value > self.risk_config.get("max_order_value", 50000):
            raise RiskCheckFailed(f"Order value {order_value:.0f} exceeds max {self.risk_config['max_order_value']:.0f}")

        if abs(self._daily_pnl) >= self.risk_config.get("max_daily_loss", 5000):
            raise RiskCheckFailed("Daily loss limit reached")

        bl = [s.upper() for s in self.risk_config.get("symbol_blacklist", [])]
        if symbol.upper() in bl:
            raise RiskCheckFailed(f"{symbol} is blacklisted")

        result = await self.broker.place_order(
            symbol=symbol, side=side, order_type=order_type,
            quantity=quantity, price=price, exchange=exchange,
        )
        if hasattr(result, '__dict__'):
            return vars(result)
        return result if isinstance(result, dict) else {"id": str(result), "status": "filled", "symbol": symbol, "side": side}

    async def cancel_order(self, order_id: str) -> bool:
        return await self.broker.cancel_order(order_id)

    async def get_positions(self):
        return await self.broker.get_positions()

    async def get_account(self):
        return await self.broker.get_account()

    def record_pnl(self, pnl: float):
        self._daily_pnl += pnl

    @property
    def is_connected(self) -> bool:
        return self._connected
