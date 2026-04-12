"""
Backtesting Engine — event-driven OHLCV backtester.
Fully self-contained, no external dependencies beyond stdlib + dataclasses.
"""
from __future__ import annotations

import math
from dataclasses import dataclass
from datetime import datetime
from typing import Any, Callable, Dict, List, Optional


# ─── Bar (single OHLCV row) ───────────────────────────────────────────────────

@dataclass
class Bar:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str = ""
    exchange: str = ""


# ─── Trade record ─────────────────────────────────────────────────────────────

@dataclass
class Trade:
    entry_time: datetime
    exit_time: Optional[datetime]
    side: str          # "long" | "short"
    entry_price: float
    exit_price: Optional[float]
    quantity: float
    pnl: float = 0.0
    commission: float = 0.0
    slippage: float = 0.0


# ─── Backtest results ─────────────────────────────────────────────────────────

@dataclass
class BacktestResults:
    symbol: str
    timeframe: str
    initial_capital: float
    final_capital: float
    total_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    avg_win: float
    avg_loss: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    equity_curve: List[Dict]
    trade_log: List[Dict]
    monthly_returns: List[Dict]

    @property
    def net_pnl(self) -> float:
        return self.final_capital - self.initial_capital


# ─── Engine ───────────────────────────────────────────────────────────────────

class BacktestEngine:
    """
    Event-driven backtesting engine.

    signal_fn(bars, position, params) → "long" | "short" | "exit" | None
    """

    def __init__(
        self,
        bars: List[Bar],
        strategy_fn: Callable,
        symbol: str = "UNKNOWN",
        timeframe: str = "15m",
        initial_capital: float = 100_000.0,
        commission_pct: float = 0.03,   # 0.03% per trade
        slippage_pct: float = 0.01,     # 0.01% per trade
        allow_short: bool = False,
        params: Optional[Dict[str, Any]] = None,
    ):
        if not bars:
            raise ValueError("bars list cannot be empty")

        self.bars = bars
        self.strategy_fn = strategy_fn
        self.symbol = symbol
        self.timeframe = timeframe
        self.initial_capital = initial_capital
        self.commission_pct = commission_pct / 100
        self.slippage_pct = slippage_pct / 100
        self.allow_short = allow_short
        self.params = params or {}

    def run(self) -> BacktestResults:
        capital = self.initial_capital
        position: Optional[Dict] = None   # active trade
        completed_trades: List[Trade] = []
        equity_curve: List[Dict] = []

        for i, bar in enumerate(self.bars):
            bars_so_far = self.bars[:i + 1]

            # Strategy signal
            try:
                signal = self.strategy_fn(bars_so_far, position, self.params)
            except Exception:
                signal = None

            # ── Entry ─────────────────────────────────────────────────────────
            if signal in ("long", "short") and position is None:
                if signal == "short" and not self.allow_short:
                    signal = None
                else:
                    entry_price = bar.close * (1 + self.slippage_pct if signal == "long" else 1 - self.slippage_pct)
                    qty = (capital * 0.95) / entry_price      # 95% of capital
                    commission = entry_price * qty * self.commission_pct
                    capital -= commission
                    position = {
                        "side": signal,
                        "entry_price": entry_price,
                        "quantity": qty,
                        "entry_time": bar.timestamp,
                        "entry_bar": i,
                    }

            # ── Exit ──────────────────────────────────────────────────────────
            elif signal == "exit" and position is not None:
                exit_price = bar.close * (1 - self.slippage_pct if position["side"] == "long" else 1 + self.slippage_pct)
                qty = position["quantity"]
                commission = exit_price * qty * self.commission_pct

                if position["side"] == "long":
                    pnl = (exit_price - position["entry_price"]) * qty - commission
                else:
                    pnl = (position["entry_price"] - exit_price) * qty - commission

                capital += pnl + position["entry_price"] * qty  # return invested capital + pnl
                # Actually, capital was not deducted on entry — just commission
                # Let's track properly:
                capital_effect = (exit_price - position["entry_price"]) * qty * (1 if position["side"] == "long" else -1) - commission
                # Recalculate — simpler model
                trade = Trade(
                    entry_time=position["entry_time"],
                    exit_time=bar.timestamp,
                    side=position["side"],
                    entry_price=position["entry_price"],
                    exit_price=exit_price,
                    quantity=qty,
                    pnl=capital_effect,
                    commission=commission,
                )
                completed_trades.append(trade)
                capital = self.initial_capital + sum(t.pnl for t in completed_trades)
                position = None

            # ── Equity curve ─────────────────────────────────────────────────
            if position:
                current_price = bar.close
                unrealized = (current_price - position["entry_price"]) * position["quantity"] * (1 if position["side"] == "long" else -1)
                current_equity = self.initial_capital + sum(t.pnl for t in completed_trades) + unrealized
            else:
                current_equity = self.initial_capital + sum(t.pnl for t in completed_trades)

            equity_curve.append({
                "time": bar.timestamp.isoformat(),
                "value": round(current_equity, 2),
            })

        # Close any open position at last bar
        if position and self.bars:
            last = self.bars[-1]
            exit_price = last.close
            qty = position["quantity"]
            pnl = (exit_price - position["entry_price"]) * qty * (1 if position["side"] == "long" else -1)
            completed_trades.append(Trade(
                entry_time=position["entry_time"],
                exit_time=last.timestamp,
                side=position["side"],
                entry_price=position["entry_price"],
                exit_price=exit_price,
                quantity=qty,
                pnl=pnl,
                commission=0,
            ))

        # ── Calculate metrics ─────────────────────────────────────────────────
        return self._calculate_metrics(completed_trades, equity_curve)

    def _calculate_metrics(self, trades: List[Trade], equity_curve: List[Dict]) -> BacktestResults:
        final_capital = self.initial_capital + sum(t.pnl for t in trades)
        total_return_pct = ((final_capital - self.initial_capital) / self.initial_capital) * 100

        wins = [t for t in trades if t.pnl > 0]
        losses = [t for t in trades if t.pnl <= 0]

        win_rate = (len(wins) / len(trades) * 100) if trades else 0
        avg_win = (sum(t.pnl for t in wins) / len(wins)) if wins else 0
        avg_loss = (sum(t.pnl for t in losses) / len(losses)) if losses else 0

        gross_profit = sum(t.pnl for t in wins)
        gross_loss = abs(sum(t.pnl for t in losses))
        profit_factor = (gross_profit / gross_loss) if gross_loss > 0 else (999.0 if gross_profit > 0 else 0.0)

        # Max drawdown
        max_dd = 0.0
        peak = self.initial_capital
        for pt in equity_curve:
            v = pt["value"]
            if v > peak:
                peak = v
            dd = (peak - v) / peak * 100 if peak > 0 else 0
            if dd > max_dd:
                max_dd = dd

        # Sharpe (daily returns from equity curve)
        values = [pt["value"] for pt in equity_curve]
        returns = [(values[i] - values[i - 1]) / values[i - 1] for i in range(1, len(values)) if values[i - 1] > 0]
        sharpe = 0.0
        sortino = 0.0
        if returns:
            avg_ret = sum(returns) / len(returns)
            std_ret = math.sqrt(sum((r - avg_ret) ** 2 for r in returns) / len(returns)) if len(returns) > 1 else 0
            sharpe = (avg_ret / std_ret * math.sqrt(252)) if std_ret > 0 else 0
            neg_returns = [r for r in returns if r < 0]
            std_neg = math.sqrt(sum(r ** 2 for r in neg_returns) / len(neg_returns)) if neg_returns else 0
            sortino = (avg_ret / std_neg * math.sqrt(252)) if std_neg > 0 else 0

        calmar = (total_return_pct / max_dd) if max_dd > 0 else 0

        trade_log = [
            {
                "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                "side": t.side,
                "entry_price": round(t.entry_price, 4),
                "exit_price": round(t.exit_price, 4) if t.exit_price else None,
                "quantity": round(t.quantity, 4),
                "pnl": round(t.pnl, 2),
            }
            for t in trades
        ]

        return BacktestResults(
            symbol=self.symbol,
            timeframe=self.timeframe,
            initial_capital=self.initial_capital,
            final_capital=round(final_capital, 2),
            total_return_pct=round(total_return_pct, 2),
            total_trades=len(trades),
            winning_trades=len(wins),
            losing_trades=len(losses),
            win_rate_pct=round(win_rate, 2),
            avg_win=round(avg_win, 2),
            avg_loss=round(avg_loss, 2),
            profit_factor=round(profit_factor, 4),
            max_drawdown_pct=round(max_dd, 2),
            sharpe_ratio=round(sharpe, 4),
            sortino_ratio=round(sortino, 4),
            calmar_ratio=round(calmar, 4),
            equity_curve=equity_curve,
            trade_log=trade_log,
            monthly_returns=[],
        )
