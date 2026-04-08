"""
Mock Market Data Adapter — Generates realistic synthetic price data.
Useful for paper trading and backtesting without real data subscriptions.

For real data, replace with:
- NSEDataAdapter (NSE/BSE)
- ZerodhaMarketDataAdapter
- BinanceMarketDataAdapter
- CSVDataAdapter (for historical CSV files)
"""
import asyncio
import math
import random
from datetime import datetime, timedelta
from typing import AsyncIterator, Dict, List, Optional, Callable, Any
from dataclasses import dataclass
import logging

logger = logging.getLogger(__name__)


@dataclass
class OHLCV:
    timestamp: datetime
    open: float
    high: float
    low: float
    close: float
    volume: float
    symbol: str
    exchange: str


class MockMarketDataAdapter:
    """
    Generates synthetic realistic price data using Geometric Brownian Motion.
    Produces live ticks and historical OHLCV bars.
    
    Implements the standard MarketDataAdapter interface.
    """

    ADAPTER_NAME = "mock"
    DISPLAY_NAME = "Mock Market Data"
    SUPPORTED_MARKETS = ["equity", "futures", "crypto", "forex"]

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self._subscribers: Dict[str, List[Callable]] = {}
        self._current_prices: Dict[str, float] = {}
        self._running = False
        self._tasks: List[asyncio.Task] = []
        
        # Default seed prices for common symbols
        self._seed_prices = {
            "RELIANCE": 2847.30,
            "TCS": 3912.60,
            "INFY": 1834.90,
            "HDFC": 1672.15,
            "HDFCBANK": 1672.15,
            "BAJFINANCE": 7214.00,
            "NIFTY50": 24832.15,
            "BANKNIFTY": 52140.60,
            "BTCUSDT": 87432.00,
            "ETHUSDT": 3221.40,
        }

    # ─── Connection ───────────────────────────────────────────────────────────

    async def connect(self) -> bool:
        self._running = True
        logger.info("MockMarketData: Connected")
        return True

    async def disconnect(self) -> bool:
        self._running = False
        for task in self._tasks:
            task.cancel()
        self._tasks.clear()
        return True

    # ─── Historical Data ─────────────────────────────────────────────────────

    async def get_historical_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCV]:
        """
        Generate synthetic historical OHLCV data using GBM.
        Replace this method in real adapters to fetch from data provider.
        """
        bars = []
        interval_minutes = self._timeframe_to_minutes(timeframe)
        current_dt = start
        seed_price = self._seed_prices.get(symbol, 1000.0)
        
        # Use symbol hash as random seed for reproducibility
        rng = random.Random(hash(symbol) % (2**32))
        
        price = seed_price
        drift = 0.0001     # Small upward drift
        volatility = self._get_volatility(symbol)

        while current_dt <= end:
            # Skip weekends
            if current_dt.weekday() < 5:
                # GBM price evolution
                dt = interval_minutes / (252 * 375)  # Fraction of trading year
                random_shock = rng.gauss(0, 1)
                price_return = math.exp(
                    (drift - 0.5 * volatility**2) * dt + volatility * math.sqrt(dt) * random_shock
                )
                prev_price = price
                price = price * price_return

                # Generate OHLC from close prices
                intrabar_vol = volatility * 0.3
                high = price * (1 + abs(rng.gauss(0, intrabar_vol)))
                low = price * (1 - abs(rng.gauss(0, intrabar_vol)))
                open_price = prev_price * (1 + rng.gauss(0, intrabar_vol * 0.5))

                # Ensure OHLC validity
                high = max(high, open_price, price)
                low = min(low, open_price, price)

                volume = rng.uniform(50000, 500000) * (1 + abs(price_return - 1) * 10)

                bars.append(OHLCV(
                    timestamp=current_dt,
                    open=round(open_price, 2),
                    high=round(high, 2),
                    low=round(low, 2),
                    close=round(price, 2),
                    volume=round(volume),
                    symbol=symbol,
                    exchange=exchange,
                ))

            current_dt += timedelta(minutes=interval_minutes)

        self._current_prices[symbol] = price
        logger.info(f"MockMarketData: Generated {len(bars)} bars for {symbol} [{timeframe}]")
        return bars

    # ─── Live Ticks ──────────────────────────────────────────────────────────

    async def subscribe_ticks(
        self,
        symbol: str,
        exchange: str,
        callback: Callable,
        tick_interval_seconds: float = 1.0,
    ):
        """Start streaming live ticks for a symbol."""
        if symbol not in self._current_prices:
            self._current_prices[symbol] = self._seed_prices.get(symbol, 1000.0)

        async def _tick_generator():
            price = self._current_prices[symbol]
            vol = self._get_volatility(symbol) * 0.1
            while self._running:
                # Small random price movement
                change = random.gauss(0, price * vol * 0.01)
                price = max(price + change, 0.01)
                self._current_prices[symbol] = price

                tick = {
                    "symbol": symbol,
                    "exchange": exchange,
                    "price": round(price, 2),
                    "timestamp": datetime.utcnow().isoformat(),
                    "bid": round(price * 0.9999, 2),
                    "ask": round(price * 1.0001, 2),
                    "volume": random.randint(100, 5000),
                }
                await callback(tick)
                await asyncio.sleep(tick_interval_seconds)

        task = asyncio.create_task(_tick_generator())
        self._tasks.append(task)
        logger.info(f"MockMarketData: Subscribed to {symbol} ticks")

    async def unsubscribe_ticks(self, symbol: str):
        """Stop streaming ticks for a symbol."""
        pass

    def get_current_price(self, symbol: str) -> Optional[float]:
        return self._current_prices.get(symbol)

    # ─── Instrument Info ─────────────────────────────────────────────────────

    async def search_instruments(self, query: str, market_type: str = "equity") -> List[Dict]:
        """Return mock instrument search results."""
        mock_instruments = [
            {"symbol": "RELIANCE", "name": "Reliance Industries Ltd", "exchange": "NSE", "type": "equity"},
            {"symbol": "TCS", "name": "Tata Consultancy Services", "exchange": "NSE", "type": "equity"},
            {"symbol": "INFY", "name": "Infosys Ltd", "exchange": "NSE", "type": "equity"},
            {"symbol": "HDFC", "name": "HDFC Bank Ltd", "exchange": "NSE", "type": "equity"},
            {"symbol": "BAJFINANCE", "name": "Bajaj Finance Ltd", "exchange": "NSE", "type": "equity"},
            {"symbol": "BTCUSDT", "name": "Bitcoin / Tether", "exchange": "BINANCE", "type": "crypto"},
            {"symbol": "NIFTY50", "name": "Nifty 50 Index", "exchange": "NSE", "type": "index"},
        ]
        q = query.upper()
        return [i for i in mock_instruments if q in i["symbol"] or q in i["name"].upper()]

    # ─── Helpers ─────────────────────────────────────────────────────────────

    def _timeframe_to_minutes(self, tf: str) -> int:
        mapping = {
            "1m": 1, "2m": 2, "3m": 3, "5m": 5, "10m": 10,
            "15m": 15, "30m": 30, "1h": 60, "2h": 120, "4h": 240,
            "1d": 375, "1w": 1875,
        }
        return mapping.get(tf, 15)

    def _get_volatility(self, symbol: str) -> float:
        """Return approximate annualized volatility by symbol type."""
        if "NIFTY" in symbol or "BANKNIFTY" in symbol:
            return 0.18
        elif "BTC" in symbol or "ETH" in symbol:
            return 0.60
        elif symbol in ("BAJFINANCE", "RELIANCE"):
            return 0.28
        else:
            return 0.22  # Default equity


# ─── CSV Data Adapter ─────────────────────────────────────────────────────────

class CSVDataAdapter:
    """
    Load historical OHLCV data from CSV files.
    CSV must have columns: datetime, open, high, low, close, volume
    """

    ADAPTER_NAME = "csv"
    DISPLAY_NAME = "CSV File Data"

    def __init__(self, config: Dict[str, Any] = None):
        self.config = config or {}
        self.data_dir = config.get("data_dir", "./data/csv")

    async def get_historical_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCV]:
        import pandas as pd
        import os

        file_path = os.path.join(self.data_dir, f"{symbol}_{timeframe}.csv")
        if not os.path.exists(file_path):
            raise FileNotFoundError(f"CSV file not found: {file_path}")

        df = pd.read_csv(file_path, parse_dates=["datetime"])
        df = df[(df["datetime"] >= start) & (df["datetime"] <= end)]

        bars = []
        for _, row in df.iterrows():
            bars.append(OHLCV(
                timestamp=row["datetime"],
                open=float(row["open"]),
                high=float(row["high"]),
                low=float(row["low"]),
                close=float(row["close"]),
                volume=float(row["volume"]),
                symbol=symbol,
                exchange=exchange,
            ))
        return bars


# ─── Base Interface ───────────────────────────────────────────────────────────

class BaseMarketDataAdapter:
    """Interface that all market data adapters must implement."""
    ADAPTER_NAME: str = ""
    DISPLAY_NAME: str = ""

    async def connect(self) -> bool: ...
    async def disconnect(self) -> bool: ...
    async def get_historical_ohlcv(self, symbol, exchange, timeframe, start, end) -> List[OHLCV]: ...
    async def subscribe_ticks(self, symbol, exchange, callback, **kwargs): ...
    async def unsubscribe_ticks(self, symbol): ...
    async def search_instruments(self, query, market_type="equity") -> List[Dict]: ...
