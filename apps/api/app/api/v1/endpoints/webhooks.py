"""
Webhooks API — receive external signals (TradingView, custom).
"""
import logging
from typing import Optional
from fastapi import APIRouter, HTTPException, Request
from pydantic import BaseModel

from app.core.config import settings

router = APIRouter()
logger = logging.getLogger(__name__)


class TradingViewSignal(BaseModel):
    """TradingView alert payload format."""
    symbol: str
    action: str          # buy | sell | exit | close_all
    price: Optional[float] = None
    quantity: Optional[float] = None
    strategy: Optional[str] = None
    exchange: Optional[str] = "NSE"
    comment: Optional[str] = None
    secret: Optional[str] = None


class CustomSignal(BaseModel):
    """Generic webhook signal format."""
    symbol: str
    action: str
    price: Optional[float] = None
    quantity: Optional[float] = None
    exchange: str = "NSE"
    metadata: Optional[dict] = None


@router.post("/tradingview", response_model=dict)
async def tradingview_webhook(signal: TradingViewSignal, request: Request):
    """
    Receive signals from TradingView Pine Script alerts.

    Setup in TradingView:
    1. Create an alert with "Webhook URL" delivery
    2. Set URL to: https://your-domain.com/api/v1/webhooks/tradingview
    3. Set message body to JSON matching TradingViewSignal schema
    4. Add your TRADINGVIEW_WEBHOOK_SECRET for security

    Example alert message:
    {
      "symbol": "{{ticker}}",
      "action": "buy",
      "price": {{close}},
      "quantity": 50,
      "secret": "your-secret-here"
    }
    """
    # Validate secret if configured
    if settings.TRADINGVIEW_WEBHOOK_SECRET:
        if not signal.secret or signal.secret != settings.TRADINGVIEW_WEBHOOK_SECRET:
            raise HTTPException(status_code=403, detail="Invalid webhook secret")

    logger.info(
        f"TradingView webhook: {signal.action.upper()} {signal.symbol} "
        f"@ {signal.price} qty={signal.quantity}"
    )

    # Route to execution engine
    result = await _route_signal(
        symbol=signal.symbol,
        action=signal.action,
        price=signal.price,
        quantity=signal.quantity,
        exchange=signal.exchange or "NSE",
        source="tradingview",
        metadata={"comment": signal.comment, "strategy": signal.strategy},
    )

    return {
        "received":  True,
        "symbol":    signal.symbol,
        "action":    signal.action,
        "processed": result["processed"],
        "message":   result.get("message", ""),
    }


@router.post("/signal", response_model=dict)
async def custom_webhook(signal: CustomSignal):
    """
    Generic webhook endpoint for custom signal sources.
    Same logic as TradingView but without the secret check by default.
    """
    logger.info(f"Custom webhook signal: {signal.action.upper()} {signal.symbol}")

    result = await _route_signal(
        symbol=signal.symbol,
        action=signal.action,
        price=signal.price,
        quantity=signal.quantity,
        exchange=signal.exchange,
        source="custom_webhook",
        metadata=signal.metadata,
    )
    return {"received": True, **result}


@router.get("/test", response_model=dict)
async def test_webhook():
    """Health check for the webhook endpoint."""
    return {
        "status": "ok",
        "endpoint": "/api/v1/webhooks/tradingview",
        "secret_configured": bool(settings.TRADINGVIEW_WEBHOOK_SECRET),
        "message": "Send POST with TradingViewSignal JSON body",
    }


async def _route_signal(
    symbol: str,
    action: str,
    price: Optional[float],
    quantity: Optional[float],
    exchange: str,
    source: str,
    metadata: Optional[dict] = None,
) -> dict:
    """
    Route an incoming webhook signal to the bot manager or execution engine.
    """
    action = action.lower().strip()

    if action not in ("buy", "sell", "exit", "close_all", "long", "short"):
        return {"processed": False, "message": f"Unknown action: {action}"}

    # Map TradingView actions to internal actions
    side_map = {"buy": "buy", "long": "buy", "sell": "sell", "short": "sell"}
    side = side_map.get(action)

    if action == "close_all":
        # TODO: trigger kill switch
        logger.warning(f"Webhook close_all from {source}")
        return {"processed": True, "message": "Close all signal received"}

    if action in ("exit",):
        # TODO: find active position for symbol and close it
        return {"processed": True, "message": f"Exit signal for {symbol} received"}

    if side:
        # TODO: route to active bot on this symbol, or place manual order
        logger.info(f"Webhook order signal: {side.upper()} {quantity or 1} {symbol} @ {price}")
        # from app.execution.bot_manager import bot_manager
        # await bot_manager.process_signal(symbol, side, quantity, price, exchange)
        return {
            "processed": True,
            "message":   f"Signal routed: {side.upper()} {symbol}",
            "source":    source,
        }

    return {"processed": False, "message": "Signal could not be routed"}
