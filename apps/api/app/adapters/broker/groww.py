"""
Groww Broker Adapter — NSE/BSE equities via Groww API v1.
Uses the JWT access token from Groww's developer portal.

Groww API docs: https://developer.groww.in/
Base URL: https://api.groww.in/v1

Supported:
- Equity orders (NSE/BSE)
- Portfolio & holdings
- Order book
- Funds/margin

Note: Groww API is rate-limited. Implement exponential backoff for prod.
"""
from __future__ import annotations
import logging
from typing import Any, Dict, List, Optional

import httpx

from app.adapters.broker.mock_broker import BaseBrokerAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class GrowwBrokerAdapter(BaseBrokerAdapter):
    """
    Groww Stock Broker API adapter.

    Authentication:
        Uses a long-lived JWT access token obtained from Groww's developer portal.
        Token is passed as Authorization: Bearer <token> on every request.

    API Reference:
        https://developer.groww.in/docs
    """

    ADAPTER_NAME     = "groww"
    DISPLAY_NAME     = "Groww"
    SUPPORTED_MARKETS = ["equity"]

    # Groww exchange segment codes
    EXCHANGE_MAP = {
        "NSE": "NSE",
        "BSE": "BSE",
    }

    # Order type mapping
    ORDER_TYPE_MAP = {
        "market":     "MARKET",
        "limit":      "LIMIT",
        "stop":       "SL_M",     # Stop Loss Market
        "stop_limit": "SL",       # Stop Loss Limit
    }

    PRODUCT_MAP = {
        "intraday": "INTRADAY",
        "delivery": "DELIVERY",
        "mtf":      "MTF",
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config       = config or {}
        self._token       = self.config.get("access_token") or settings.GROWW_ACCESS_TOKEN
        self._secret      = self.config.get("api_secret")   or settings.GROWW_API_SECRET
        self._base_url    = self.config.get("base_url")      or settings.GROWW_BASE_URL
        self._client: Optional[httpx.AsyncClient] = None
        self._connected   = False
        self._account_id: Optional[str] = None

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type":  "application/json",
            "Accept":        "application/json",
        }

    async def connect(self) -> bool:
        if not self._token:
            raise ValueError(
                "GROWW_ACCESS_TOKEN not set in .env\n"
                "Get it from: https://developer.groww.in/"
            )

        self._client = httpx.AsyncClient(
            base_url=self._base_url,
            headers=self._headers,
            timeout=15.0,
            verify=True,
        )

        try:
            # Verify token by fetching user profile
            resp = await self._client.get("/user/info")
            if resp.status_code == 401:
                raise ValueError("Invalid Groww access token. Please regenerate.")
            resp.raise_for_status()

            data = resp.json()
            user = data.get("data", data)
            self._account_id = user.get("userId") or user.get("accountId")

            logger.info(
                f"Groww connected — User: {user.get('name', 'unknown')} "
                f"| Account: {self._account_id}"
            )
            self._connected = True
            return True

        except httpx.HTTPStatusError as e:
            logger.error(f"Groww connection failed: HTTP {e.response.status_code} — {e.response.text}")
            return False
        except Exception as e:
            logger.error(f"Groww connection error: {e}")
            return False

    async def disconnect(self) -> bool:
        if self._client:
            await self._client.aclose()
            self._client = None
        self._connected = False
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected and self._client is not None

    # ─── Orders ───────────────────────────────────────────────────────────────

    async def place_order(
        self,
        symbol: str,
        side: str,          # "buy" | "sell"
        order_type: str,    # "market" | "limit" | "stop" | "stop_limit"
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        exchange: str = "NSE",
        product: str = "intraday",
        **kwargs,
    ) -> Dict[str, Any]:
        if not self._client:
            raise RuntimeError("Groww adapter not connected. Call connect() first.")

        payload = {
            "tradingSymbol":    symbol.upper(),
            "exchange":         self.EXCHANGE_MAP.get(exchange.upper(), "NSE"),
            "transactionType":  "BUY" if side.lower() == "buy" else "SELL",
            "orderType":        self.ORDER_TYPE_MAP.get(order_type.lower(), "MARKET"),
            "productType":      self.PRODUCT_MAP.get(product.lower(), "INTRADAY"),
            "quantity":         int(quantity),
            "price":            price or 0,
            "triggerPrice":     stop_price or 0,
            "validity":         "DAY",
        }

        try:
            resp = await self._client.post("/orders", json=payload)
            resp.raise_for_status()
            data = resp.json().get("data", resp.json())

            order_id = data.get("orderId") or data.get("id", "unknown")
            logger.info(
                f"Groww: {side.upper()} {quantity} {symbol} @ {order_type} "
                f"— Order ID: {order_id}"
            )
            return {
                "id":       order_id,
                "status":   "open",
                "symbol":   symbol.upper(),
                "side":     side.lower(),
                "quantity": quantity,
            }

        except httpx.HTTPStatusError as e:
            logger.error(f"Groww place_order failed: {e.response.status_code} — {e.response.text}")
            raise RuntimeError(f"Groww order failed: {e.response.text}")

    async def cancel_order(self, order_id: str) -> bool:
        try:
            resp = await self._client.delete(f"/orders/{order_id}")
            return resp.status_code in (200, 204)
        except Exception as e:
            logger.error(f"Groww cancel_order failed: {e}")
            return False

    async def cancel_all_orders(self, symbol: Optional[str] = None) -> int:
        open_orders = await self.get_open_orders(symbol)
        count = 0
        for order in open_orders:
            if await self.cancel_order(order["id"]):
                count += 1
        return count

    async def get_order(self, order_id: str) -> Optional[Dict]:
        try:
            resp = await self._client.get(f"/orders/{order_id}")
            resp.raise_for_status()
            data = resp.json().get("data", {})
            return self._normalise_order(data)
        except Exception as e:
            logger.error(f"Groww get_order failed: {e}")
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        try:
            resp = await self._client.get("/orders", params={"status": "OPEN"})
            resp.raise_for_status()
            orders_data = resp.json().get("data", {}).get("orders", [])
            orders = [self._normalise_order(o) for o in orders_data]
            if symbol:
                orders = [o for o in orders if o.get("symbol", "").upper() == symbol.upper()]
            return orders
        except Exception as e:
            logger.error(f"Groww get_open_orders failed: {e}")
            return []

    # ─── Positions ────────────────────────────────────────────────────────────

    async def get_positions(self) -> List[Dict]:
        """Fetch open positions (intraday net positions)."""
        try:
            resp = await self._client.get("/portfolio/positions")
            resp.raise_for_status()
            positions = resp.json().get("data", {}).get("positions", [])
            return [self._normalise_position(p) for p in positions if p.get("netQty", 0) != 0]
        except Exception as e:
            logger.error(f"Groww get_positions failed: {e}")
            return []

    async def get_position(self, symbol: str) -> Optional[Dict]:
        positions = await self.get_positions()
        return next((p for p in positions if p.get("symbol", "").upper() == symbol.upper()), None)

    async def get_holdings(self) -> List[Dict]:
        """Fetch long-term delivery holdings."""
        try:
            resp = await self._client.get("/portfolio/holdings")
            resp.raise_for_status()
            holdings = resp.json().get("data", {}).get("holdings", [])
            return [
                {
                    "symbol":        h.get("tradingSymbol", ""),
                    "exchange":      h.get("exchange", "NSE"),
                    "side":          "buy",
                    "quantity":      h.get("quantity", 0),
                    "avg_price":     h.get("averagePrice", 0),
                    "current_price": h.get("lastPrice", 0),
                    "unrealized_pnl":h.get("pnl", 0),
                    "realized_pnl":  0.0,
                    "product":       "delivery",
                }
                for h in holdings
            ]
        except Exception as e:
            logger.error(f"Groww get_holdings failed: {e}")
            return []

    # ─── Account ──────────────────────────────────────────────────────────────

    async def get_account(self) -> Dict[str, Any]:
        try:
            resp = await self._client.get("/user/margins")
            resp.raise_for_status()
            data = resp.json().get("data", {})
            equity = data.get("equity", {})
            return {
                "cash":              float(equity.get("availableMargin", 0)),
                "total_value":       float(equity.get("net", 0)),
                "used_margin":       float(equity.get("utilisedMargin", 0)),
                "available_margin":  float(equity.get("availableMargin", 0)),
                "payin":             float(equity.get("payin", 0)),
                "account_id":        self._account_id,
                "currency":          "INR",
            }
        except Exception as e:
            logger.error(f"Groww get_account failed: {e}")
            return {}

    async def get_order_history(self, limit: int = 50) -> List[Dict]:
        """Get complete order history for today."""
        try:
            resp = await self._client.get("/orders", params={"limit": limit})
            resp.raise_for_status()
            orders = resp.json().get("data", {}).get("orders", [])
            return [self._normalise_order(o) for o in orders]
        except Exception as e:
            logger.error(f"Groww get_order_history failed: {e}")
            return []

    # ─── Market Data (basic quotes via Groww) ─────────────────────────────────

    async def get_quote(self, symbol: str, exchange: str = "NSE") -> Optional[Dict]:
        """Get live quote for a symbol."""
        try:
            resp = await self._client.get(
                f"/marketdata/quote/{exchange}/{symbol}"
            )
            if resp.status_code == 200:
                data = resp.json().get("data", {})
                return {
                    "symbol":   symbol,
                    "exchange": exchange,
                    "ltp":      data.get("ltp", 0),
                    "open":     data.get("open", 0),
                    "high":     data.get("high", 0),
                    "low":      data.get("low", 0),
                    "close":    data.get("close", 0),
                    "volume":   data.get("volume", 0),
                    "change":   data.get("change", 0),
                    "change_pct": data.get("changePct", 0),
                }
            return None
        except Exception as e:
            logger.debug(f"Groww get_quote failed for {symbol}: {e}")
            return None

    # ─── Normalisers ──────────────────────────────────────────────────────────

    def _normalise_order(self, o: Dict) -> Dict:
        STATUS_MAP = {
            "COMPLETE":         "filled",
            "OPEN":             "open",
            "CANCELLED":        "cancelled",
            "REJECTED":         "rejected",
            "TRIGGER_PENDING":  "open",
            "PENDING":          "open",
            "MODIFIED":         "open",
            "PARTIALLY_FILLED": "partially_filled",
        }
        return {
            "id":              o.get("orderId", o.get("id", "")),
            "broker_id":       o.get("orderId", ""),
            "symbol":          o.get("tradingSymbol", ""),
            "exchange":        o.get("exchange", "NSE"),
            "side":            "buy" if o.get("transactionType", "").upper() == "BUY" else "sell",
            "order_type":      o.get("orderType", "MARKET").lower().replace("_", ""),
            "quantity":        float(o.get("quantity", 0)),
            "price":           float(o.get("price", 0)),
            "status":          STATUS_MAP.get(o.get("status", "").upper(), "unknown"),
            "filled_quantity": float(o.get("filledQuantity", 0)),
            "avg_fill_price":  float(o.get("averagePrice", 0)),
            "product":         o.get("productType", "INTRADAY"),
            "placed_at":       o.get("orderTime", ""),
        }

    def _normalise_position(self, p: Dict) -> Dict:
        net_qty = int(p.get("netQty", 0))
        return {
            "symbol":        p.get("tradingSymbol", ""),
            "exchange":      p.get("exchange", "NSE"),
            "side":          "buy" if net_qty > 0 else "sell",
            "quantity":      abs(net_qty),
            "avg_price":     float(p.get("netPrice", p.get("avgPrice", 0))),
            "current_price": float(p.get("ltp", 0)),
            "unrealized_pnl":float(p.get("unrealisedPnl", p.get("pnl", 0))),
            "realized_pnl":  float(p.get("realisedPnl", 0)),
            "product":       p.get("productType", "INTRADAY"),
        }
