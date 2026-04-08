"""
Alpaca Markets Broker Adapter
For US equities and ETFs. Supports paper and live trading.

Requirements:
    pip install alpaca-trade-api
    OR pip install alpaca-py (newer SDK)

Setup:
    1. Create account at https://alpaca.markets/
    2. Get API keys from the dashboard
    3. Set ALPACA_API_KEY, ALPACA_API_SECRET in .env
    4. Set ALPACA_BASE_URL=https://paper-api.alpaca.markets (paper)
       OR ALPACA_BASE_URL=https://api.alpaca.markets (live)
"""
from typing import Any, Dict, List, Optional
import logging
import httpx

from app.adapters.broker.mock_broker import BaseBrokerAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)


class AlpacaBrokerAdapter(BaseBrokerAdapter):

    ADAPTER_NAME = "alpaca"
    DISPLAY_NAME = "Alpaca Markets (US)"
    SUPPORTED_MARKETS = ["equity"]

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._api_key    = self.config.get("api_key")    or settings.ALPACA_API_KEY
        self._api_secret = self.config.get("api_secret") or settings.ALPACA_API_SECRET
        self._base_url   = self.config.get("base_url")   or settings.ALPACA_BASE_URL
        self._client: Optional[httpx.AsyncClient] = None
        self._connected = False

    @property
    def _headers(self) -> Dict[str, str]:
        return {
            "APCA-API-KEY-ID":     self._api_key or "",
            "APCA-API-SECRET-KEY": self._api_secret or "",
            "Content-Type":        "application/json",
        }

    async def connect(self) -> bool:
        if not self._api_key or not self._api_secret:
            raise ValueError("ALPACA_API_KEY and ALPACA_API_SECRET must be set in .env")

        self._client = httpx.AsyncClient(base_url=self._base_url, headers=self._headers, timeout=10.0)

        try:
            resp = await self._client.get("/v2/account")
            resp.raise_for_status()
            acct = resp.json()
            logger.info(f"Alpaca connected. Account: {acct.get('id', '')[:8]}... | "
                        f"Cash: ${float(acct.get('cash', 0)):,.2f} | "
                        f"Mode: {'paper' if 'paper' in self._base_url else 'live'}")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Alpaca connection failed: {e}")
            return False

    async def disconnect(self) -> bool:
        if self._client:
            await self._client.aclose()
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
        time_in_force: str = "gtc",
        **kwargs,
    ) -> Dict[str, Any]:
        payload = {
            "symbol":        symbol.upper(),
            "qty":           str(quantity),
            "side":          side.lower(),
            "type":          {"market": "market", "limit": "limit", "stop": "stop", "stop_limit": "stop_limit"}.get(order_type, "market"),
            "time_in_force": time_in_force,
        }
        if price and order_type in ("limit", "stop_limit"):
            payload["limit_price"] = str(price)
        if stop_price and order_type in ("stop", "stop_limit"):
            payload["stop_price"] = str(stop_price)

        resp = await self._client.post("/v2/orders", json=payload)
        resp.raise_for_status()
        o = resp.json()
        return self._normalise_order(o)

    async def cancel_order(self, order_id: str) -> bool:
        try:
            resp = await self._client.delete(f"/v2/orders/{order_id}")
            return resp.status_code in (200, 204)
        except Exception:
            return False

    async def get_order(self, order_id: str) -> Optional[Dict]:
        try:
            resp = await self._client.get(f"/v2/orders/{order_id}")
            return self._normalise_order(resp.json()) if resp.status_code == 200 else None
        except Exception:
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        params = {"status": "open"}
        if symbol:
            params["symbols"] = symbol.upper()
        resp = await self._client.get("/v2/orders", params=params)
        return [self._normalise_order(o) for o in resp.json()] if resp.status_code == 200 else []

    async def get_positions(self) -> List[Dict]:
        resp = await self._client.get("/v2/positions")
        if resp.status_code != 200:
            return []
        return [{
            "symbol":        p["symbol"],
            "exchange":      "NASDAQ",
            "side":          "buy" if int(p["qty"]) > 0 else "sell",
            "quantity":      abs(float(p["qty"])),
            "avg_price":     float(p["avg_entry_price"]),
            "current_price": float(p["current_price"]),
            "unrealized_pnl":float(p["unrealized_pl"]),
            "realized_pnl":  0.0,
        } for p in resp.json()]

    async def get_position(self, symbol: str) -> Optional[Dict]:
        try:
            resp = await self._client.get(f"/v2/positions/{symbol.upper()}")
            if resp.status_code == 200:
                p = resp.json()
                return {"symbol": p["symbol"], "quantity": abs(float(p["qty"])), "avg_price": float(p["avg_entry_price"]), "current_price": float(p["current_price"]), "unrealized_pnl": float(p["unrealized_pl"])}
            return None
        except Exception:
            return None

    async def get_account(self) -> Dict[str, Any]:
        resp = await self._client.get("/v2/account")
        if resp.status_code != 200:
            return {}
        a = resp.json()
        return {
            "cash":               float(a.get("cash", 0)),
            "total_value":        float(a.get("portfolio_value", 0)),
            "buying_power":       float(a.get("buying_power", 0)),
            "equity":             float(a.get("equity", 0)),
            "long_market_value":  float(a.get("long_market_value", 0)),
            "short_market_value": float(a.get("short_market_value", 0)),
        }

    def _normalise_order(self, o: Dict) -> Dict:
        return {
            "id":              o.get("id", ""),
            "broker_id":       o.get("id", ""),
            "symbol":          o.get("symbol", ""),
            "exchange":        "NASDAQ",
            "side":            o.get("side", ""),
            "order_type":      o.get("type", ""),
            "quantity":        float(o.get("qty", 0)),
            "price":           float(o.get("limit_price") or 0),
            "status":          o.get("status", ""),
            "filled_quantity": float(o.get("filled_qty", 0)),
            "avg_fill_price":  float(o.get("filled_avg_price") or 0),
        }
