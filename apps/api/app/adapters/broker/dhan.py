"""
Dhan Broker Adapter — NSE/BSE equities, futures, options.

Requirements:
    pip install dhanhq

Setup:
    1. Create account at https://dhan.co/
    2. Generate API credentials in the Dhan developer console
    3. Set DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN in .env
    4. Access tokens are long-lived (no daily refresh needed)
"""
from typing import Any, Dict, List, Optional
import logging

from app.adapters.broker.mock_broker import BaseBrokerAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from dhanhq import dhanhq
    HAS_DHAN = True
except ImportError:
    HAS_DHAN = False
    logger.warning("dhanhq not installed. Run: pip install dhanhq")


class DhanBrokerAdapter(BaseBrokerAdapter):
    """
    Dhan broker adapter.
    Uses the dhanhq Python SDK.
    """

    ADAPTER_NAME = "dhan"
    DISPLAY_NAME = "Dhan"
    SUPPORTED_MARKETS = ["equity", "futures", "options"]

    EXCHANGE_MAP = {
        "NSE": "NSE_EQ",
        "BSE": "BSE",
        "NFO": "NSE_FNO",
        "MCX": "MCX_COMM",
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._client_id    = self.config.get("client_id")    or settings.DHAN_CLIENT_ID
        self._access_token = self.config.get("access_token") or settings.DHAN_ACCESS_TOKEN
        self._dhan: Optional[Any] = None
        self._connected = False

    async def connect(self) -> bool:
        if not HAS_DHAN:
            raise RuntimeError("dhanhq not installed. Run: pip install dhanhq")
        if not self._client_id or not self._access_token:
            raise ValueError("DHAN_CLIENT_ID and DHAN_ACCESS_TOKEN must be set in .env")
        try:
            self._dhan = dhanhq(self._client_id, self._access_token)
            # Verify by fetching fund limits
            resp = self._dhan.get_fund_limits()
            if resp.get("status") == "success":
                logger.info(f"Dhan connected: {self._client_id}")
                self._connected = True
                return True
            else:
                logger.error(f"Dhan auth failed: {resp}")
                return False
        except Exception as e:
            logger.error(f"Dhan connection failed: {e}")
            return False

    async def disconnect(self) -> bool:
        self._dhan = None
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
        exchange: str = "NSE",
        security_id: str = "",
        product_type: str = "INTRADAY",
        **kwargs,
    ) -> Dict[str, Any]:
        if not self._dhan:
            raise RuntimeError("Not connected")

        dhan_side     = "BUY" if side == "buy" else "SELL"
        dhan_type     = {"market": "MARKET", "limit": "LIMIT", "stop": "STOP_LOSS_MARKET", "stop_limit": "STOP_LOSS"}.get(order_type, "MARKET")
        dhan_exchange = self.EXCHANGE_MAP.get(exchange.upper(), "NSE_EQ")

        params: Dict[str, Any] = {
            "security_id":    security_id or symbol,  # Dhan uses numeric security IDs
            "exchange_segment": dhan_exchange,
            "transaction_type": dhan_side,
            "quantity":       int(quantity),
            "order_type":     dhan_type,
            "product_type":   product_type,
            "price":          price or 0,
            "trigger_price":  stop_price or 0,
        }

        try:
            resp = self._dhan.place_order(**params)
            if resp.get("status") == "success":
                order_id = resp["data"]["orderId"]
                logger.info(f"Dhan order: {order_id} | {dhan_side} {quantity} {symbol}")
                return {"id": order_id, "status": "open", "symbol": symbol, "side": side}
            else:
                raise RuntimeError(f"Dhan order failed: {resp.get('remarks', 'unknown error')}")
        except Exception as e:
            logger.error(f"Dhan place_order failed: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        try:
            resp = self._dhan.cancel_order(order_id)
            return resp.get("status") == "success"
        except Exception as e:
            logger.error(f"Dhan cancel_order failed: {e}")
            return False

    async def get_order(self, order_id: str) -> Optional[Dict]:
        try:
            resp = self._dhan.get_order_by_id(order_id)
            if resp.get("status") == "success":
                return self._normalise_order(resp["data"])
            return None
        except Exception:
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        try:
            resp = self._dhan.get_order_list()
            if resp.get("status") != "success":
                return []
            orders = [
                self._normalise_order(o) for o in resp.get("data", [])
                if o.get("orderStatus") in ("PENDING", "TRANSIT", "PART_TRADED")
            ]
            return orders
        except Exception as e:
            logger.error(f"Dhan get_open_orders failed: {e}")
            return []

    async def get_positions(self) -> List[Dict]:
        try:
            resp = self._dhan.get_positions()
            if resp.get("status") != "success":
                return []
            result = []
            for p in resp.get("data", []):
                net_qty = int(p.get("netQty", 0))
                if net_qty != 0:
                    result.append({
                        "symbol":        p.get("tradingSymbol", ""),
                        "exchange":      p.get("exchangeSegment", ""),
                        "side":          "buy" if net_qty > 0 else "sell",
                        "quantity":      abs(net_qty),
                        "avg_price":     float(p.get("costPrice", 0)),
                        "current_price": float(p.get("lastTradedPrice", 0)),
                        "unrealized_pnl":float(p.get("unrealizedProfit", 0)),
                        "realized_pnl":  float(p.get("realizedProfit", 0)),
                    })
            return result
        except Exception as e:
            logger.error(f"Dhan get_positions failed: {e}")
            return []

    async def get_position(self, symbol: str) -> Optional[Dict]:
        positions = await self.get_positions()
        return next((p for p in positions if p["symbol"] == symbol), None)

    async def get_account(self) -> Dict[str, Any]:
        try:
            resp = self._dhan.get_fund_limits()
            if resp.get("status") == "success":
                data = resp["data"]
                return {
                    "cash":             float(data.get("availabelBalance", 0)),
                    "total_value":      float(data.get("sodLimit", 0)),
                    "used_margin":      float(data.get("utilisedAmount", 0)),
                    "available_margin": float(data.get("availabelBalance", 0)),
                }
            return {}
        except Exception as e:
            logger.error(f"Dhan get_account failed: {e}")
            return {}

    def _normalise_order(self, o: Dict) -> Dict:
        status_map = {
            "TRADED":       "filled",
            "PENDING":      "open",
            "TRANSIT":      "open",
            "PART_TRADED":  "partially_filled",
            "CANCELLED":    "cancelled",
            "REJECTED":     "rejected",
            "EXPIRED":      "cancelled",
        }
        return {
            "id":              o.get("orderId", ""),
            "broker_id":       o.get("orderId", ""),
            "symbol":          o.get("tradingSymbol", ""),
            "exchange":        o.get("exchangeSegment", ""),
            "side":            "buy" if o.get("transactionType") == "BUY" else "sell",
            "order_type":      o.get("orderType", "").lower(),
            "quantity":        float(o.get("quantity", 0)),
            "price":           float(o.get("price", 0)),
            "status":          status_map.get(o.get("orderStatus", ""), "unknown"),
            "filled_quantity": float(o.get("tradedQuantity", 0)),
            "avg_fill_price":  float(o.get("tradedPrice", 0)),
        }
