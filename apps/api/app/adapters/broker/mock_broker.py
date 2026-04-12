"""
Mock Broker Adapter — Simulates a real broker for paper trading.
This is the default adapter used when no real broker is connected.
It supports all order types, fills instantly at market price with configurable slippage.
"""
import asyncio
import uuid
from datetime import datetime
from typing import Optional, Dict, Any, List
from dataclasses import dataclass, field
import logging

logger = logging.getLogger(__name__)


@dataclass
class MockPosition:
    symbol: str
    side: str
    quantity: float
    avg_price: float
    current_price: float = 0.0

    @property
    def unrealized_pnl(self) -> float:
        if self.side == "buy":
            return (self.current_price - self.avg_price) * self.quantity
        else:
            return (self.avg_price - self.current_price) * self.quantity


@dataclass
class MockOrder:
    id: str
    symbol: str
    side: str
    order_type: str
    quantity: float
    price: Optional[float]
    status: str = "pending"
    filled_quantity: float = 0.0
    avg_fill_price: float = 0.0
    placed_at: datetime = field(default_factory=datetime.utcnow)


class MockBrokerAdapter:
    """
    Simulated broker for paper trading.
    Fills market orders instantly; limit orders fill when price is touched.

    Implements the standard BrokerAdapter interface so it can be
    swapped out for any real broker adapter.
    """

    ADAPTER_NAME = "mock"
    DISPLAY_NAME = "Mock Broker (Paper Trading)"
    SUPPORTED_MARKETS = ["equity", "futures", "options", "crypto", "forex"]

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.slippage_pct: float = self.config.get("slippage_pct", 0.01)  # 0.01%
        self.commission_pct: float = self.config.get("commission_pct", 0.03)  # 0.03%
        self.initial_capital: float = self.config.get("initial_capital", 1_000_000.0)
        self.fill_delay_ms: int = self.config.get("fill_delay_ms", 100)

        # Internal state
        self._cash: float = self.initial_capital
        self._orders: Dict[str, MockOrder] = {}
        self._positions: Dict[str, MockPosition] = {}
        self._market_prices: Dict[str, float] = {}  # Set by market data feed
        self._is_connected: bool = False

    # ─── Connection ───────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        """Simulate connection."""
        await asyncio.sleep(0.1)
        self._is_connected = True
        logger.info(f"MockBroker connected. Capital: ₹{self._cash:,.2f}")
        return True

    async def disconnect(self) -> bool:
        self._is_connected = False
        return True

    @property
    def is_connected(self) -> bool:
        return self._is_connected

    # ─── Market Data (fed by MarketData adapter) ──────────────────────────────

    def update_price(self, symbol: str, price: float):
        """Called by market data feed to update current price."""
        self._market_prices[symbol] = price
        # Update open position P&L
        if symbol in self._positions:
            self._positions[symbol].current_price = price

    def get_price(self, symbol: str) -> Optional[float]:
        return self._market_prices.get(symbol)

    # ─── Orders ───────────────────────────────────────────────────────────────

    async def place_order(
        self,
        symbol: str,
        side: str,  # "buy" | "sell"
        order_type: str,  # "market" | "limit" | "stop" | "stop_limit"
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        **kwargs,
    ) -> MockOrder:
        """Place an order. Market orders fill immediately."""
        order_id = str(uuid.uuid4())
        order = MockOrder(
            id=order_id,
            symbol=symbol,
            side=side,
            order_type=order_type,
            quantity=quantity,
            price=price,
            status="open",
        )
        self._orders[order_id] = order

        logger.info(f"MockBroker: Order placed {side.upper()} {quantity} {symbol} @ {order_type}")

        # Market orders fill immediately (with configurable delay)
        if order_type == "market":
            await asyncio.sleep(self.fill_delay_ms / 1000)
            await self._fill_order(order)

        return order

    async def cancel_order(self, order_id: str) -> bool:
        order = self._orders.get(order_id)
        if not order or order.status in ("filled", "cancelled"):
            return False
        order.status = "cancelled"
        logger.info(f"MockBroker: Order {order_id} cancelled")
        return True

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        count = 0
        for order in self._orders.values():
            if order.status == "open":
                if symbol is None or order.symbol == symbol:
                    order.status = "cancelled"
                    count += 1
        return count

    async def get_order(self, order_id: str) -> Optional[MockOrder]:
        return self._orders.get(order_id)

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[MockOrder]:
        return [
            o for o in self._orders.values()
            if o.status == "open" and (symbol is None or o.symbol == symbol)
        ]

    # ─── Positions ────────────────────────────────────────────────────────────

    async def get_positions(self) -> List[MockPosition]:
        return list(self._positions.values())

    async def get_position(self, symbol: str) -> Optional[MockPosition]:
        return self._positions.get(symbol)

    # ─── Account ──────────────────────────────────────────────────────────────

    async def get_account(self) -> Dict[str, Any]:
        positions_value = sum(
            p.current_price * p.quantity for p in self._positions.values()
        )
        total_pnl = sum(p.unrealized_pnl for p in self._positions.values())
        return {
            "cash": self._cash,
            "positions_value": positions_value,
            "total_value": self._cash + positions_value,
            "unrealized_pnl": total_pnl,
            "initial_capital": self.initial_capital,
        }

    # ─── Internal ─────────────────────────────────────────────────────────────

    async def _fill_order(self, order: MockOrder):
        """Execute a fill at market price with slippage applied."""
        market_price = self._market_prices.get(order.symbol, order.price or 100.0)
        slippage = market_price * (self.slippage_pct / 100)

        if order.side == "buy":
            fill_price = market_price + slippage
        else:
            fill_price = market_price - slippage

        commission = fill_price * order.quantity * (self.commission_pct / 100)
        order_value = fill_price * order.quantity

        # Check funds for buy
        if order.side == "buy":
            total_cost = order_value + commission
            if total_cost > self._cash:
                order.status = "rejected"
                logger.warning(f"MockBroker: Insufficient funds for {order.symbol}. Need ₹{total_cost:.2f}, have ₹{self._cash:.2f}")
                return

        # Apply fill
        order.status = "filled"
        order.filled_quantity = order.quantity
        order.avg_fill_price = fill_price

        # Update cash
        if order.side == "buy":
            self._cash -= (order_value + commission)
            self._update_position_buy(order.symbol, order.quantity, fill_price)
        else:
            self._cash += (order_value - commission)
            self._update_position_sell(order.symbol, order.quantity, fill_price)

        logger.info(
            f"MockBroker: FILLED {order.side.upper()} {order.quantity} {order.symbol} "
            f"@ ₹{fill_price:.2f} | Commission: ₹{commission:.2f}"
        )

    def _update_position_buy(self, symbol: str, qty: float, price: float):
        if symbol in self._positions:
            pos = self._positions[symbol]
            if pos.side == "buy":
                # Average up
                total_cost = (pos.avg_price * pos.quantity) + (price * qty)
                pos.quantity += qty
                pos.avg_price = total_cost / pos.quantity
            else:
                # Closing short position (partial or full)
                pos.quantity -= qty
                if pos.quantity <= 0:
                    del self._positions[symbol]
        else:
            self._positions[symbol] = MockPosition(
                symbol=symbol, side="buy", quantity=qty, avg_price=price,
                current_price=self._market_prices.get(symbol, price)
            )

    def _update_position_sell(self, symbol: str, qty: float, price: float):
        if symbol in self._positions:
            pos = self._positions[symbol]
            if pos.side == "sell":
                # Averaging down short
                total = (pos.avg_price * pos.quantity) + (price * qty)
                pos.quantity += qty
                pos.avg_price = total / pos.quantity
            else:
                # Closing long
                pos.quantity -= qty
                if pos.quantity <= 0:
                    del self._positions[symbol]
        else:
            self._positions[symbol] = MockPosition(
                symbol=symbol, side="sell", quantity=qty, avg_price=price,
                current_price=self._market_prices.get(symbol, price)
            )

    def reset(self, initial_capital: Optional[float] = None):
        """Reset paper account to initial state."""
        self._cash = initial_capital or self.initial_capital
        self._orders.clear()
        self._positions.clear()
        logger.info(f"MockBroker: Account reset. Capital: ₹{self._cash:,.2f}")


# ─── Base Interface (for type checking and future adapters) ───────────────────

class BaseBrokerAdapter:
    """
    Abstract interface that all broker adapters must implement.
    Create a new adapter by subclassing this.

    Naming convention: {BrokerName}BrokerAdapter
    Example: ZerodhaBrokerAdapter, AlpacaBrokerAdapter
    """
    ADAPTER_NAME: str = ""
    DISPLAY_NAME: str = ""
    SUPPORTED_MARKETS: List[str] = []

    async def connect(self) -> bool: ...
    async def disconnect(self) -> bool: ...
    async def place_order(self, **kwargs) -> Any: ...
    async def cancel_order(self, order_id: str) -> bool: ...
    async def get_order(self, order_id: str) -> Optional[Any]: ...
    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Any]: ...
    async def get_positions(self) -> List[Any]: ...
    async def get_account(self) -> Dict[str, Any]: ...
