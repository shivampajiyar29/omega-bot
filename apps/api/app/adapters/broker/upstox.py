"""
Upstox Broker Adapter — NSE/BSE equities and futures.

Requirements:
    pip install upstox-python-sdk

Setup:
    1. Create app at https://developer.upstox.com/
    2. Get API key and secret
    3. Complete OAuth2 flow to get access token
    4. Set UPSTOX_API_KEY, UPSTOX_API_SECRET, UPSTOX_ACCESS_TOKEN in .env

Note: Upstox v2 uses OAuth2 — access tokens expire and need daily refresh.
"""
from typing import Any, Dict, List, Optional
import logging

from app.adapters.broker.mock_broker import BaseBrokerAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    import upstox_client
    from upstox_client.rest import ApiException  # noqa: F401
    HAS_UPSTOX = True
except ImportError:
    HAS_UPSTOX = False
    logger.warning("upstox-python-sdk not installed. Run: pip install upstox-python-sdk")


class UpstoxBrokerAdapter(BaseBrokerAdapter):
    """
    Upstox Pro API broker adapter.
    Uses the official Upstox Python SDK v2.
    """

    ADAPTER_NAME     = "upstox"
    DISPLAY_NAME     = "Upstox"
    SUPPORTED_MARKETS = ["equity", "futures", "options"]

    # Upstox exchange segment codes
    EXCHANGE_MAP = {
        "NSE":  "NSE_EQ",
        "BSE":  "BSE_EQ",
        "NFO":  "NSE_FO",
        "BFO":  "BSE_FO",
        "MCX":  "MCX_FO",
        "CDS":  "CDS_FO",
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._api_key      = self.config.get("api_key")     or getattr(settings, "UPSTOX_API_KEY", None)
        self._api_secret   = self.config.get("api_secret")  or getattr(settings, "UPSTOX_API_SECRET", None)
        self._access_token = self.config.get("access_token")or getattr(settings, "UPSTOX_ACCESS_TOKEN", None)
        self._order_api    = None
        self._portfolio_api= None
        self._connected    = False

    async def connect(self) -> bool:
        if not HAS_UPSTOX:
            raise RuntimeError("upstox-python-sdk not installed. Run: pip install upstox-python-sdk")
        if not self._access_token:
            raise ValueError(
                "UPSTOX_ACCESS_TOKEN not set. Complete OAuth2 flow:\n"
                f"1. Visit: https://api.upstox.com/v2/login/authorization/dialog?response_type=code&client_id={self._api_key}&redirect_uri=YOUR_REDIRECT\n"
                "2. Exchange auth code for access token"
            )
        try:
            config = upstox_client.Configuration()
            config.access_token = self._access_token

            client = upstox_client.ApiClient(config)
            self._order_api     = upstox_client.OrderApi(client)
            self._portfolio_api = upstox_client.PortfolioApi(client)

            # Verify by fetching holdings
            holdings = self._portfolio_api.get_holdings(api_version="2.0")
            logger.info(f"Upstox connected. Holdings count: {len(holdings.data or [])}")
            self._connected = True
            return True
        except Exception as e:
            logger.error(f"Upstox connection failed: {e}")
            return False

    async def disconnect(self) -> bool:
        self._connected = False
        self._order_api = None
        self._portfolio_api = None
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
        product: str = "D",  # D=Delivery, I=Intraday
        **kwargs,
    ) -> Dict[str, Any]:
        if not self._order_api:
            raise RuntimeError("Not connected")

        upstox_type = {
            "market":     "MARKET",
            "limit":      "LIMIT",
            "stop":       "SL-M",
            "stop_limit": "SL",
        }.get(order_type, "MARKET")

        instrument_key = f"{self.EXCHANGE_MAP.get(exchange.upper(), 'NSE_EQ')}|{symbol}"

        body = upstox_client.PlaceOrderRequest(
            quantity=int(quantity),
            product=product,
            validity="DAY",
            price=price or 0,
            tag="omegabot",
            instrument_token=instrument_key,
            order_type=upstox_type,
            transaction_type="BUY" if side == "buy" else "SELL",
            disclosed_quantity=0,
            trigger_price=stop_price or 0,
            is_amo=False,
        )

        try:
            resp = self._order_api.place_order(body, api_version="2.0")
            order_id = resp.data.order_id
            logger.info(f"Upstox order: {order_id} | {side.upper()} {quantity} {symbol}")
            return {"id": order_id, "status": "open", "symbol": symbol, "side": side}
        except Exception as e:
            logger.error(f"Upstox place_order failed: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        try:
            self._order_api.cancel_order(order_id, api_version="2.0")
            return True
        except Exception as e:
            logger.error(f"Upstox cancel_order failed: {e}")
            return False

    async def get_order(self, order_id: str) -> Optional[Dict]:
        try:
            resp = self._order_api.get_order_details(api_version="2.0", order_id=order_id)
            if resp.data:
                return self._normalise_order(resp.data[0].__dict__)
            return None
        except Exception:
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        try:
            resp = self._order_api.get_order_book(api_version="2.0")
            orders = [
                self._normalise_order(o.__dict__)
                for o in (resp.data or [])
                if o.status in ("open", "trigger pending", "modified")
            ]
            if symbol:
                orders = [o for o in orders if o["symbol"] == symbol.upper()]
            return orders
        except Exception as e:
            logger.error(f"Upstox get_open_orders failed: {e}")
            return []

    async def get_positions(self) -> List[Dict]:
        try:
            resp = self._portfolio_api.get_positions(api_version="2.0")
            result = []
            for p in resp.data or []:
                net_qty = int(p.net_quantity or 0)
                if net_qty != 0:
                    result.append({
                        "symbol":        p.trading_symbol or "",
                        "exchange":      p.exchange or "",
                        "side":          "buy" if net_qty > 0 else "sell",
                        "quantity":      abs(net_qty),
                        "avg_price":     float(p.average_price or 0),
                        "current_price": float(p.last_price or 0),
                        "unrealized_pnl":float(p.unrealised_profit or 0),
                        "realized_pnl":  float(p.realised_profit or 0),
                    })
            return result
        except Exception as e:
            logger.error(f"Upstox get_positions failed: {e}")
            return []

    async def get_position(self, symbol: str) -> Optional[Dict]:
        positions = await self.get_positions()
        return next((p for p in positions if p["symbol"] == symbol.upper()), None)

    async def get_account(self) -> Dict[str, Any]:
        try:
            user_api = upstox_client.UserApi(
                upstox_client.ApiClient(
                    upstox_client.Configuration(access_token=self._access_token)
                )
            )
            funds = user_api.get_user_fund_margin(api_version="2.0", segment="SEC")
            data = funds.data
            return {
                "cash":             float(data.available_margin or 0),
                "total_value":      float(data.used_margin or 0) + float(data.available_margin or 0),
                "used_margin":      float(data.used_margin or 0),
                "available_margin": float(data.available_margin or 0),
            }
        except Exception as e:
            logger.error(f"Upstox get_account failed: {e}")
            return {}

    def _normalise_order(self, o: Dict) -> Dict:
        status_map = {
            "complete":         "filled",
            "open":             "open",
            "cancelled":        "cancelled",
            "rejected":         "rejected",
            "trigger pending":  "open",
            "modified":         "open",
        }
        return {
            "id":              o.get("order_id", ""),
            "broker_id":       o.get("order_id", ""),
            "symbol":          o.get("trading_symbol", ""),
            "exchange":        o.get("exchange", ""),
            "side":            "buy" if o.get("transaction_type") == "BUY" else "sell",
            "order_type":      (o.get("order_type") or "").lower(),
            "quantity":        float(o.get("quantity", 0)),
            "price":           float(o.get("price", 0)),
            "status":          status_map.get((o.get("status") or "").lower(), "unknown"),
            "filled_quantity": float(o.get("filled_quantity", 0)),
            "avg_fill_price":  float(o.get("average_price", 0)),
        }

    @staticmethod
    def get_auth_url(api_key: str, redirect_uri: str) -> str:
        """Return the OAuth2 authorization URL for getting auth code."""
        return (
            f"https://api.upstox.com/v2/login/authorization/dialog"
            f"?response_type=code&client_id={api_key}&redirect_uri={redirect_uri}"
        )
