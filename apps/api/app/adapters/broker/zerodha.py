"""
Zerodha / Kite Connect Broker Adapter
Implements the BaseBrokerAdapter interface for Zerodha's Kite API.

Requirements:
    pip install kiteconnect

Setup:
    1. Get API key from https://kite.trade/
    2. Set ZERODHA_API_KEY and ZERODHA_API_SECRET in .env
    3. Run the auth flow to get access token
    4. Set ZERODHA_ACCESS_TOKEN in .env (refreshes daily)

Exchange codes: NSE, BSE, NFO (futures/options), MCX (commodities)
"""
from typing import Any, Dict, List, Optional
import logging

from app.adapters.broker.mock_broker import BaseBrokerAdapter, MockOrder, MockPosition
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from kiteconnect import KiteConnect
    HAS_KITE = True
except ImportError:
    HAS_KITE = False
    logger.warning("kiteconnect not installed. Run: pip install kiteconnect")


class ZerodhaBrokerAdapter(BaseBrokerAdapter):
    """
    Zerodha Kite Connect broker adapter.
    All order methods mirror the mock broker interface.
    """

    ADAPTER_NAME = "zerodha"
    DISPLAY_NAME = "Zerodha / Kite Connect"
    SUPPORTED_MARKETS = ["equity", "futures", "options", "commodity"]

    # Exchange code mapping
    EXCHANGE_MAP = {
        "NSE": "NSE",
        "BSE": "BSE",
        "NFO": "NFO",   # Futures & Options
        "MCX": "MCX",   # Commodities
        "CDS": "CDS",   # Currency derivatives
        "BFO": "BFO",   # BSE F&O
    }

    # Product type mapping
    PRODUCT_MAP = {
        "intraday": "MIS",  # Margin Intraday Square-off
        "delivery": "CNC",  # Cash and Carry
        "futures":  "NRML", # Normal (for F&O)
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._api_key    = self.config.get("api_key")    or settings.ZERODHA_API_KEY
        self._api_secret = self.config.get("api_secret") or settings.ZERODHA_API_SECRET
        self._access_token = self.config.get("access_token") or settings.ZERODHA_ACCESS_TOKEN
        self._kite: Optional[Any] = None
        self._connected = False

    # ─── Connection ───────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        if not HAS_KITE:
            raise RuntimeError("kiteconnect not installed. Run: pip install kiteconnect")
        if not self._api_key:
            raise ValueError("ZERODHA_API_KEY not set in .env")
        if not self._access_token:
            raise ValueError(
                "ZERODHA_ACCESS_TOKEN not set. "
                "Complete the auth flow at: "
                f"https://kite.trade/connect/login?api_key={self._api_key}"
            )
        try:
            self._kite = KiteConnect(api_key=self._api_key)
            self._kite.set_access_token(self._access_token)
            # Verify by fetching profile
            profile = self._kite.profile()
            logger.info(f"Zerodha connected: {profile.get('user_name', 'unknown')}")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Zerodha connection failed: {e}")
            self._connected = False
            return False

    async def disconnect(self) -> bool:
        if self._kite:
            try:
                self._kite.invalidate_access_token()
            except Exception:
                pass
        self._connected = False
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ─── Orders ───────────────────────────────────────────────────────────────

    async def place_order(
        self,
        symbol: str,
        side: str,         # "buy" | "sell"
        order_type: str,   # "market" | "limit" | "stop" | "stop_limit"
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        exchange: str = "NSE",
        product: str = "intraday",
        **kwargs,
    ) -> Dict[str, Any]:
        if not self._kite:
            raise RuntimeError("Not connected")

        kite_order_type = {
            "market":     "MARKET",
            "limit":      "LIMIT",
            "stop":       "SL-M",
            "stop_limit": "SL",
        }.get(order_type, "MARKET")

        kite_transaction = "BUY" if side == "buy" else "SELL"
        kite_product     = self.PRODUCT_MAP.get(product, "MIS")
        kite_exchange    = self.EXCHANGE_MAP.get(exchange.upper(), exchange.upper())

        params = {
            "tradingsymbol":  symbol,
            "exchange":       kite_exchange,
            "transaction_type": kite_transaction,
            "quantity":       int(quantity),
            "product":        kite_product,
            "order_type":     kite_order_type,
            "validity":       "DAY",
        }
        if price and order_type in ("limit", "stop_limit"):
            params["price"] = price
        if stop_price and order_type in ("stop", "stop_limit"):
            params["trigger_price"] = stop_price

        try:
            order_id = self._kite.place_order(variety="regular", **params)
            logger.info(f"Zerodha order placed: {order_id} | {kite_transaction} {quantity} {symbol}")
            return {"id": str(order_id), "status": "open", "symbol": symbol, "side": side}
        except Exception as e:
            logger.error(f"Zerodha order failed: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        if not self._kite:
            return False
        try:
            self._kite.cancel_order(variety="regular", order_id=order_id)
            return True
        except Exception as e:
            logger.error(f"Zerodha cancel order failed: {e}")
            return False

    async def get_order(self, order_id: str) -> Optional[Dict]:
        if not self._kite:
            return None
        try:
            orders = self._kite.orders()
            for o in orders:
                if str(o["order_id"]) == str(order_id):
                    return self._normalise_order(o)
            return None
        except Exception as e:
            logger.error(f"Zerodha get_order failed: {e}")
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        if not self._kite:
            return []
        try:
            orders = self._kite.orders()
            result = [self._normalise_order(o) for o in orders if o["status"] in ("OPEN", "TRIGGER PENDING")]
            if symbol:
                result = [o for o in result if o["symbol"] == symbol]
            return result
        except Exception as e:
            logger.error(f"Zerodha get_open_orders failed: {e}")
            return []

    # ─── Positions ────────────────────────────────────────────────────────────

    async def get_positions(self) -> List[Dict]:
        if not self._kite:
            return []
        try:
            positions = self._kite.positions()
            result = []
            for p in positions.get("net", []):
                if p["quantity"] != 0:
                    result.append({
                        "symbol":       p["tradingsymbol"],
                        "exchange":     p["exchange"],
                        "side":         "buy" if p["quantity"] > 0 else "sell",
                        "quantity":     abs(p["quantity"]),
                        "avg_price":    p["average_price"],
                        "current_price":p["last_price"],
                        "unrealized_pnl": p["unrealised"],
                        "realized_pnl":   p["realised"],
                    })
            return result
        except Exception as e:
            logger.error(f"Zerodha get_positions failed: {e}")
            return []

    async def get_position(self, symbol: str) -> Optional[Dict]:
        positions = await self.get_positions()
        return next((p for p in positions if p["symbol"] == symbol), None)

    # ─── Account ──────────────────────────────────────────────────────────────

    async def get_account(self) -> Dict[str, Any]:
        if not self._kite:
            return {}
        try:
            margins = self._kite.margins()
            equity = margins.get("equity", {})
            return {
                "cash":             equity.get("available", {}).get("live_balance", 0),
                "total_value":      equity.get("net", 0),
                "used_margin":      equity.get("utilised", {}).get("debits", 0),
                "available_margin": equity.get("available", {}).get("cash", 0),
            }
        except Exception as e:
            logger.error(f"Zerodha get_account failed: {e}")
            return {}

    # ─── Auth helpers ─────────────────────────────────────────────────────────

    def get_login_url(self) -> str:
        """Returns the Kite Connect login URL for getting a request token."""
        if not self._api_key:
            raise ValueError("ZERODHA_API_KEY not set")
        return f"https://kite.trade/connect/login?api_key={self._api_key}&v=3"

    def generate_access_token(self, request_token: str) -> str:
        """
        Exchange request token for access token.
        Call after user completes login and you get the request_token from redirect URL.
        """
        if not HAS_KITE:
            raise RuntimeError("kiteconnect not installed")
        kite = KiteConnect(api_key=self._api_key)
        data = kite.generate_session(request_token, api_secret=self._api_secret)
        access_token = data["access_token"]
        logger.info(f"New Zerodha access token generated. Add to .env: ZERODHA_ACCESS_TOKEN={access_token}")
        return access_token

    # ─── Helpers ──────────────────────────────────────────────────────────────

    def _normalise_order(self, o: Dict) -> Dict:
        return {
            "id":             str(o.get("order_id", "")),
            "broker_id":      str(o.get("order_id", "")),
            "symbol":         o.get("tradingsymbol", ""),
            "exchange":       o.get("exchange", ""),
            "side":           "buy" if o.get("transaction_type") == "BUY" else "sell",
            "order_type":     o.get("order_type", "").lower(),
            "quantity":       o.get("quantity", 0),
            "price":          o.get("price", 0),
            "status":         o.get("status", "").lower(),
            "filled_quantity":o.get("filled_quantity", 0),
            "avg_fill_price": o.get("average_price", 0),
        }
