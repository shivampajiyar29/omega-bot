"""Decision engine — combine model outputs into BUY/SELL/HOLD."""
from __future__ import annotations
import logging
import os
from dataclasses import dataclass
from typing import Literal

logger = logging.getLogger(__name__)

BUY_THRESHOLD  = float(os.getenv("BUY_THRESHOLD",  "0.62"))
SELL_THRESHOLD = float(os.getenv("SELL_THRESHOLD", "0.62"))
XGB_WEIGHT     = float(os.getenv("XGB_WEIGHT",     "0.45"))
LSTM_WEIGHT    = float(os.getenv("LSTM_WEIGHT",    "0.55"))

Signal = Literal["BUY", "SELL", "HOLD"]


@dataclass
class Prediction:
    signal: Signal
    confidence: float
    agreement: bool
    xgb_signal: str
    xgb_confidence: float
    combined_score: float
    reasoning: str
    target_price: float = 0.0
    direction_pct: float = 0.0


def combine_predictions(xgb_pred: int, xgb_conf: float,
                        current_price: float = 0.0) -> Prediction:
    """Simple XGBoost-only decision (LSTM optional)."""
    xgb_label = "UP" if xgb_pred == 1 else "DOWN"
    xgb_score = xgb_conf if xgb_pred == 1 else -xgb_conf
    combined = XGB_WEIGHT * xgb_score + LSTM_WEIGHT * xgb_score  # same for now

    if xgb_pred == 1 and combined > BUY_THRESHOLD:
        signal: Signal = "BUY"
        direction_pct = xgb_conf * 2.0
    elif xgb_pred == 0 and abs(combined) > SELL_THRESHOLD:
        signal = "SELL"
        direction_pct = -xgb_conf * 2.0
    else:
        signal = "HOLD"
        direction_pct = 0.0

    target = current_price * (1 + direction_pct / 100) if current_price > 0 else 0.0

    reasoning = (
        f"XGBoost: {xgb_label} ({xgb_conf:.1%}). "
        f"Combined score: {combined:.3f}. "
        f"{'Signal exceeds threshold.' if signal != 'HOLD' else 'Below threshold → HOLD.'}"
    )

    return Prediction(
        signal=signal,
        confidence=round(abs(combined), 4),
        agreement=True,
        xgb_signal=xgb_label,
        xgb_confidence=round(xgb_conf, 4),
        combined_score=round(combined, 4),
        reasoning=reasoning,
        target_price=round(target, 2),
        direction_pct=round(direction_pct, 2),
    )
