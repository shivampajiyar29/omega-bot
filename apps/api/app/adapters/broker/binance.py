"""
Binance Broker Adapter — Crypto spot and futures trading.

Requirements:
    pip install python-binance

Setup:
    1. Create API keys at https://www.binance.com/en/my/settings/api-management
    2. Enable "Spot & Margin Trading" permissions (NOT withdrawal)
    3. Set BINANCE_API_KEY, BINANCE_API_SECRET in .env
    4. Set BINANCE_TESTNET=true for testnet, false for live

IMPORTANT: Never enable withdrawal permissions on trading API keys.
"""
from typing import Any, Dict, List, Optional
import logging

from app.adapters.broker.mock_broker import BaseBrokerAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from binance import AsyncClient as BinanceAsyncClient
    from binance.exceptions import BinanceAPIException  # noqa: F401
    HAS_BINANCE = True
except ImportError:
    HAS_BINANCE = False
    logger.warning("python-binance not installed. Run: pip install python-binance")


class BinanceBrokerAdapter(BaseBrokerAdapter):
    """
    Binance crypto broker adapter.
    Supports spot trading on all USDT pairs.
    Set BINANCE_TESTNET=true for paper trading on testnet.
    """

    ADAPTER_NAME = "binance"
    DISPLAY_NAME = "Binance"
    SUPPORTED_MARKETS = ["crypto"]

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._api_key    = self.config.get("api_key")    or settings.BINANCE_API_KEY
        self._api_secret = self.config.get("api_secret") or settings.BINANCE_API_SECRET
        self._testnet    = self.config.get("testnet", settings.BINANCE_TESTNET)
        self._client: Optional[Any] = None
        self._connected = False

    async def connect(self) -> bool:
        if not HAS_BINANCE:
            raise RuntimeError("python-binance not installed. Run: pip install python-binance")
        if not self._api_key or not self._api_secret:
            raise ValueError("BINANCE_API_KEY and BINANCE_API_SECRET must be set in .env")
        try:
            self._client = await BinanceAsyncClient.create(
                api_key=self._api_key,
                api_secret=self._api_secret,
                testnet=self._testnet,
            )
            account = await self._client.get_account()
            balances = {b["asset"]: float(b["free"]) for b in account["balances"] if float(b["free"]) > 0}
            mode = "TESTNET" if self._testnet else "LIVE"
            logger.info(f"Binance connected [{mode}]. Non-zero balances: {list(balances.keys())[:5]}")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Binance connection failed: {e}")
            return False

    async def disconnect(self) -> bool:
        if self._client:
            await self._client.close_connection()
        self._connected = False
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("Not connected")

        binance_side = "BUY" if side == "buy" else "SELL"
        binance_type = {
            "market":     "MARKET",
            "limit":      "LIMIT",
            "stop":       "STOP_LOSS",
            "stop_limit": "STOP_LOSS_LIMIT",
        }.get(order_type, "MARKET")

        params: Dict[str, Any] = {
            "symbol":    symbol.upper(),
            "side":      binance_side,
            "type":      binance_type,
            "quantity":  f"{quantity:.8f}".rstrip("0").rstrip("."),
        }

        if binance_type == "LIMIT":
            params["price"]       = str(price)
            params["timeInForce"] = "GTC"
        if binance_type in ("STOP_LOSS", "STOP_LOSS_LIMIT") and stop_price:
            params["stopPrice"] = str(stop_price)

        try:
            order = await self._client.create_order(**params)
            logger.info(f"Binance order: {order['orderId']} | {binance_side} {quantity} {symbol}")
            return self._normalise_order(order)
        except Exception as e:
            logger.error(f"Binance order failed: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        # We need symbol to cancel — store it in order_id as "SYMBOL:id"
        try:
            parts = order_id.split(":")
            symbol, oid = (parts[0], parts[1]) if len(parts) == 2 else ("BTCUSDT", order_id)
            await self._client.cancel_order(symbol=symbol, orderId=int(oid))
            return True
        except Exception as e:
            logger.error(f"Binance cancel order failed: {e}")
            return False

    async def get_order(self, order_id: str) -> Optional[Dict]:
        try:
            parts = order_id.split(":")
            symbol, oid = (parts[0], parts[1]) if len(parts) == 2 else ("BTCUSDT", order_id)
            order = await self._client.get_order(symbol=symbol, orderId=int(oid))
            return self._normalise_order(order)
        except Exception:
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        try:
            params = {}
            if symbol:
                params["symbol"] = symbol.upper()
            orders = await self._client.get_open_orders(**params)
            return [self._normalise_order(o) for o in orders]
        except Exception as e:
            logger.error(f"Binance get_open_orders failed: {e}")
            return []

    async def get_positions(self) -> List[Dict]:
        """For spot trading, positions = non-zero balances."""
        try:
            account = await self._client.get_account()
            positions = []
            for b in account["balances"]:
                free = float(b["free"])
                locked = float(b["locked"])
                total = free + locked
                if total > 0 and b["asset"] not in ("USDT", "BUSD", "USDC", "BNB"):
                    positions.append({
                        "symbol":   b["asset"] + "USDT",
                        "exchange": "BINANCE",
                        "side":     "buy",
                        "quantity": total,
                        "avg_price": 0.0,  # Binance spot doesn't track avg price directly
                        "current_price": 0.0,
                        "unrealized_pnl": 0.0,
                        "realized_pnl":   0.0,
                    })
            return positions
        except Exception as e:
            logger.error(f"Binance get_positions failed: {e}")
            return []

    async def get_position(self, symbol: str) -> Optional[Dict]:
        positions = await self.get_positions()
        return next((p for p in positions if p["symbol"] == symbol.upper()), None)

    async def get_account(self) -> Dict[str, Any]:
        try:
            account = await self._client.get_account()
            usdt = next(
                (float(b["free"]) for b in account["balances"] if b["asset"] == "USDT"), 0.0
            )
            return {
                "cash":        usdt,
                "total_value": usdt,
                "currency":    "USDT",
                "can_trade":   account.get("canTrade", True),
            }
        except Exception as e:
            logger.error(f"Binance get_account failed: {e}")
            return {}

    def _normalise_order(self, o: Dict) -> Dict:
        status_map = {
            "NEW":              "open",
            "PARTIALLY_FILLED": "partially_filled",
            "FILLED":           "filled",
            "CANCELED":         "cancelled",
            "REJECTED":         "rejected",
            "EXPIRED":          "cancelled",
        }
        symbol = o.get("symbol", "")
        return {
            "id":              f"{symbol}:{o.get('orderId', '')}",
            "broker_id":       str(o.get("orderId", "")),
            "symbol":          symbol,
            "exchange":        "BINANCE",
            "side":            "buy" if o.get("side") == "BUY" else "sell",
            "order_type":      o.get("type", "").lower(),
            "quantity":        float(o.get("origQty", 0)),
            "price":           float(o.get("price", 0)),
            "status":          status_map.get(o.get("status", ""), "unknown"),
            "filled_quantity": float(o.get("executedQty", 0)),
            "avg_fill_price":  float(o.get("price", 0)),
        }
