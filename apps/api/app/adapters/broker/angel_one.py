"""
Angel One / Angel Broking Smart API Adapter
For NSE/BSE equities, futures, and options.

Requirements:
    pip install smartapi-python

Setup:
    1. Create API credentials at https://smartapi.angelbroking.com/
    2. Get your Client ID, MPIN, and TOTP key from the app
    3. Set ANGEL_ONE_CLIENT_ID, ANGEL_ONE_MPIN, ANGEL_ONE_TOTP_KEY in .env
    4. TOTP refreshes every 30s — use pyotp to generate it

Notes:
    - Angel One uses instrument tokens, not plain symbols
    - Requires fetching the instrument master file for token lookup
"""
from typing import Any, Dict, List, Optional
import logging

from app.adapters.broker.mock_broker import BaseBrokerAdapter
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from SmartApi import SmartConnect
    import pyotp
    HAS_ANGEL = True
except ImportError:
    HAS_ANGEL = False
    logger.warning("SmartApi or pyotp not installed. Run: pip install smartapi-python pyotp")


class AngelOneBrokerAdapter(BaseBrokerAdapter):
    """
    Angel One Smart API broker adapter.
    Supports NSE/BSE equities, futures, and options.
    """

    ADAPTER_NAME = "angel_one"
    DISPLAY_NAME = "Angel One"
    SUPPORTED_MARKETS = ["equity", "futures", "options"]

    # Exchange mapping
    EXCHANGE_MAP = {
        "NSE": "NSE",
        "BSE": "BSE",
        "NFO": "NFO",
        "MCX": "MCX",
        "CDS": "CDS",
    }

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._client_id = self.config.get("client_id") or settings.ANGEL_ONE_CLIENT_ID
        self._mpin      = self.config.get("mpin")      or settings.ANGEL_ONE_MPIN
        self._totp_key  = self.config.get("totp_key")  or settings.ANGEL_ONE_TOTP_KEY
        self._smart: Optional[Any] = None
        self._auth_token: Optional[str] = None
        self._connected = False
        self._instrument_cache: Dict[str, str] = {}  # symbol → token

    async def connect(self) -> bool:
        if not HAS_ANGEL:
            raise RuntimeError("SmartApi not installed. Run: pip install smartapi-python pyotp")
        if not all([self._client_id, self._mpin, self._totp_key]):
            raise ValueError("ANGEL_ONE_CLIENT_ID, ANGEL_ONE_MPIN, ANGEL_ONE_TOTP_KEY must be set")

        try:
            self._smart = SmartConnect(api_key=self._client_id)
            totp = pyotp.TOTP(self._totp_key).now()

            data = self._smart.generateSession(self._client_id, self._mpin, totp)
            if data["status"]:
                self._auth_token = data["data"]["jwtToken"]
                logger.info(f"Angel One connected: {self._client_id}")
                self._connected = True
                return True
            else:
                logger.error(f"Angel One auth failed: {data.get('message', 'unknown')}")
                return False
        except Exception as e:
            logger.error(f"Angel One connection failed: {e}")
            return False

    async def disconnect(self) -> bool:
        if self._smart:
            try:
                self._smart.terminateSession(self._client_id)
            except Exception:
                pass
        self._connected = False
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _get_token(self, symbol: str, exchange: str = "NSE") -> str:
        """
        Get instrument token for a symbol.
        In production, this should lookup the master instrument file.
        Returns symbol as fallback for now.
        """
        cache_key = f"{exchange}:{symbol}"
        if cache_key in self._instrument_cache:
            return self._instrument_cache[cache_key]
        # TODO: download and parse the instrument master CSV
        # https://margincalculator.angelbroking.com/OpenAPI_File/files/OpenAPIScripMaster.json
        logger.warning(f"Instrument token not in cache for {symbol}. Use instrument master lookup.")
        return symbol

    async def place_order(
        self,
        symbol: str,
        side: str,
        order_type: str,
        quantity: float,
        price: Optional[float] = None,
        stop_price: Optional[float] = None,
        exchange: str = "NSE",
        product: str = "INTRADAY",  # INTRADAY | DELIVERY | CARRYFORWARD
        **kwargs,
    ) -> Dict[str, Any]:
        if not self._smart:
            raise RuntimeError("Not connected")

        token = self._get_token(symbol, exchange)

        order_params = {
            "variety":          "NORMAL",
            "tradingsymbol":    symbol,
            "symboltoken":      token,
            "transactiontype":  "BUY" if side == "buy" else "SELL",
            "exchange":         self.EXCHANGE_MAP.get(exchange.upper(), exchange.upper()),
            "ordertype":        {"market": "MARKET", "limit": "LIMIT", "stop": "STOPLOSS_MARKET", "stop_limit": "STOPLOSS_LIMIT"}.get(order_type, "MARKET"),
            "producttype":      product,
            "duration":         "DAY",
            "quantity":         str(int(quantity)),
        }

        if price and order_type in ("limit", "stop_limit"):
            order_params["price"] = str(price)
        if stop_price and order_type in ("stop", "stop_limit"):
            order_params["triggerprice"] = str(stop_price)

        try:
            resp = self._smart.placeOrder(order_params)
            if resp["status"]:
                order_id = resp["data"]["orderid"]
                logger.info(f"Angel One order: {order_id} | {side.upper()} {quantity} {symbol}")
                return {"id": order_id, "status": "open", "symbol": symbol, "side": side}
            else:
                raise RuntimeError(f"Angel One order failed: {resp.get('message', 'unknown')}")
        except Exception as e:
            logger.error(f"Angel One place_order failed: {e}")
            raise

    async def cancel_order(self, order_id: str) -> bool:
        try:
            resp = self._smart.cancelOrder(order_id, "NORMAL")
            return resp.get("status", False)
        except Exception as e:
            logger.error(f"Angel One cancel_order failed: {e}")
            return False

    async def get_order(self, order_id: str) -> Optional[Dict]:
        try:
            book = self._smart.orderBook()
            if book["status"]:
                for o in book["data"] or []:
                    if o["orderid"] == order_id:
                        return self._normalise_order(o)
            return None
        except Exception:
            return None

    async def get_open_orders(self, symbol: Optional[str] = None) -> List[Dict]:
        try:
            book = self._smart.orderBook()
            if not book["status"]:
                return []
            orders = [
                self._normalise_order(o) for o in (book["data"] or [])
                if o.get("orderstatus") in ("open", "trigger pending")
            ]
            if symbol:
                orders = [o for o in orders if o["symbol"] == symbol]
            return orders
        except Exception as e:
            logger.error(f"Angel One get_open_orders failed: {e}")
            return []

    async def get_positions(self) -> List[Dict]:
        try:
            pos = self._smart.position()
            if not pos["status"]:
                return []
            result = []
            for p in pos["data"] or []:
                net_qty = int(p.get("netqty", 0))
                if net_qty != 0:
                    result.append({
                        "symbol":        p.get("tradingsymbol", ""),
                        "exchange":      p.get("exchange", ""),
                        "side":          "buy" if net_qty > 0 else "sell",
                        "quantity":      abs(net_qty),
                        "avg_price":     float(p.get("netavgprice", 0)),
                        "current_price": float(p.get("ltp", 0)),
                        "unrealized_pnl":float(p.get("unrealised", 0)),
                        "realized_pnl":  float(p.get("realised", 0)),
                    })
            return result
        except Exception as e:
            logger.error(f"Angel One get_positions failed: {e}")
            return []

    async def get_position(self, symbol: str) -> Optional[Dict]:
        positions = await self.get_positions()
        return next((p for p in positions if p["symbol"] == symbol), None)

    async def get_account(self) -> Dict[str, Any]:
        try:
            rms = self._smart.rmsLimit()
            if rms["status"]:
                data = rms["data"]
                return {
                    "cash":             float(data.get("availablecash", 0)),
                    "total_value":      float(data.get("net", 0)),
                    "used_margin":      float(data.get("utiliseddebits", 0)),
                    "available_margin": float(data.get("availablecash", 0)),
                }
            return {}
        except Exception as e:
            logger.error(f"Angel One get_account failed: {e}")
            return {}

    def _normalise_order(self, o: Dict) -> Dict:
        status_map = {
            "complete": "filled", "open": "open", "cancelled": "cancelled",
            "rejected": "rejected", "trigger pending": "open",
        }
        return {
            "id":              o.get("orderid", ""),
            "broker_id":       o.get("orderid", ""),
            "symbol":          o.get("tradingsymbol", ""),
            "exchange":        o.get("exchange", ""),
            "side":            "buy" if o.get("transactiontype") == "BUY" else "sell",
            "order_type":      o.get("ordertype", "").lower(),
            "quantity":        float(o.get("quantity", 0)),
            "price":           float(o.get("price", 0)),
            "status":          status_map.get(o.get("orderstatus", "").lower(), "unknown"),
            "filled_quantity": float(o.get("filledshares", 0)),
            "avg_fill_price":  float(o.get("averageprice", 0)),
        }
