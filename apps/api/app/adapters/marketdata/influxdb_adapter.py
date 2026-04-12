"""
InfluxDB Market Data Adapter
Stores and retrieves OHLCV data from InfluxDB Cloud.
Used for high-performance time-series queries during backtesting.

Measurement schema:
  measurement: ohlcv
  tags: symbol, exchange, timeframe
  fields: open, high, low, close, volume
  time: timestamp (nanoseconds)
"""
from __future__ import annotations
import logging
from datetime import datetime
from typing import Any, Dict, List

from app.adapters.marketdata.mock_data import OHLCV
from app.core.config import settings

logger = logging.getLogger(__name__)

try:
    from influxdb_client import InfluxDBClient, WriteOptions  # noqa: F401
    from influxdb_client.client.write_api import SYNCHRONOUS  # noqa: F401
    from influxdb_client.client.influxdb_client_async import InfluxDBClientAsync
    HAS_INFLUX = True
except ImportError:
    HAS_INFLUX = False
    logger.warning("influxdb-client not installed. Run: pip install influxdb-client")


class InfluxDBMarketDataAdapter:
    """
    InfluxDB Cloud adapter for OHLCV storage and retrieval.
    Integrates with your RedisLabs + InfluxDB stack.

    Write path: Live ticks → InfluxDB (write_api)
    Read path:  Backtest → InfluxDB query → OHLCV bars
    """

    ADAPTER_NAME     = "influxdb"
    DISPLAY_NAME     = "InfluxDB Cloud (Time-Series)"
    SUPPORTED_MARKETS = ["equity", "futures", "crypto", "forex"]

    def __init__(self, config: Dict[str, Any] = None):
        self.config  = config or {}
        self._url    = self.config.get("url")    or settings.INFLUXDB_URL
        self._token  = self.config.get("token")  or settings.INFLUXDB_TOKEN
        self._org    = self.config.get("org")    or settings.INFLUXDB_ORG or "omegabot"
        self._bucket = self.config.get("bucket") or settings.INFLUXDB_BUCKET
        self._client = None
        self._write_api = None
        self._query_api = None
        self._connected = False

    async def connect(self) -> bool:
        if not HAS_INFLUX:
            logger.error("influxdb-client not installed")
            return False
        if not self._url or not self._token:
            logger.warning("InfluxDB URL/token not configured, skipping")
            return False

        try:
            self._client = InfluxDBClientAsync(
                url=self._url,
                token=self._token,
                org=self._org,
            )
            # Ping to verify
            ready = await self._client.ping()
            if ready:
                logger.info(f"InfluxDB connected: {self._url} | Bucket: {self._bucket}")
                self._connected = True
                return True
            else:
                logger.error("InfluxDB ping failed")
                return False
        except Exception as e:
            logger.error(f"InfluxDB connection failed: {e}")
            return False

    async def disconnect(self) -> bool:
        if self._client:
            await self._client.close()
        self._connected = False
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

    # ─── Write OHLCV ─────────────────────────────────────────────────────────

    async def write_ohlcv(self, bars: List[OHLCV], timeframe: str = "1d"):
        """Write OHLCV bars to InfluxDB."""
        if not self._connected or not self._client:
            return

        from influxdb_client import Point  # noqa: F401
        from influxdb_client.domain.write_precision import WritePrecision

        points = []
        for bar in bars:
            p = (
                Point("ohlcv")
                .tag("symbol",    bar.symbol)
                .tag("exchange",  bar.exchange)
                .tag("timeframe", timeframe)
                .field("open",    float(bar.open))
                .field("high",    float(bar.high))
                .field("low",     float(bar.low))
                .field("close",   float(bar.close))
                .field("volume",  float(bar.volume))
                .time(bar.timestamp, WritePrecision.SECONDS)
            )
            points.append(p)

        try:
            write_api = self._client.write_api()
            await write_api.write(bucket=self._bucket, record=points)
            logger.debug(f"InfluxDB: wrote {len(points)} bars for {bars[0].symbol if bars else '?'}")
        except Exception as e:
            logger.error(f"InfluxDB write failed: {e}")

    # ─── Read OHLCV ──────────────────────────────────────────────────────────

    async def get_historical_ohlcv(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        start: datetime,
        end: datetime,
    ) -> List[OHLCV]:
        """
        Query OHLCV bars from InfluxDB.
        Falls back to mock data if InfluxDB has no records.
        """
        if not self._connected or not self._client:
            return await self._fallback_mock(symbol, exchange, timeframe, start, end)

        start_str = start.strftime("%Y-%m-%dT%H:%M:%SZ")
        end_str   = end.strftime("%Y-%m-%dT%H:%M:%SZ")

        flux_query = f'''
from(bucket: "{self._bucket}")
  |> range(start: {start_str}, stop: {end_str})
  |> filter(fn: (r) => r["_measurement"] == "ohlcv")
  |> filter(fn: (r) => r["symbol"] == "{symbol}")
  |> filter(fn: (r) => r["exchange"] == "{exchange}")
  |> filter(fn: (r) => r["timeframe"] == "{timeframe}")
  |> pivot(rowKey: ["_time"], columnKey: ["_field"], valueColumn: "_value")
  |> sort(columns: ["_time"])
'''
        try:
            query_api = self._client.query_api()
            tables = await query_api.query(flux_query)

            bars = []
            for table in tables:
                for record in table.records:
                    row = record.values
                    bars.append(OHLCV(
                        timestamp=record.get_time().replace(tzinfo=None),
                        open=float(row.get("open", 0)),
                        high=float(row.get("high", 0)),
                        low=float(row.get("low", 0)),
                        close=float(row.get("close", 0)),
                        volume=float(row.get("volume", 0)),
                        symbol=symbol,
                        exchange=exchange,
                    ))

            if bars:
                logger.info(f"InfluxDB: retrieved {len(bars)} bars for {symbol} [{timeframe}]")
                return bars
            else:
                logger.info(f"InfluxDB: no data for {symbol}, using mock fallback")
                return await self._fallback_mock(symbol, exchange, timeframe, start, end)

        except Exception as e:
            logger.error(f"InfluxDB query failed: {e}")
            return await self._fallback_mock(symbol, exchange, timeframe, start, end)

    async def _fallback_mock(self, symbol, exchange, timeframe, start, end) -> List[OHLCV]:
        """Fall back to mock data generator when InfluxDB has no data."""
        from app.adapters.marketdata.mock_data import MockMarketDataAdapter
        mock = MockMarketDataAdapter()
        await mock.connect()
        return await mock.get_historical_ohlcv(symbol, exchange, timeframe, start, end)

    async def search_instruments(self, query: str, market_type: str = "equity") -> List[Dict]:
        from app.adapters.marketdata.mock_data import MockMarketDataAdapter
        mock = MockMarketDataAdapter()
        return await mock.search_instruments(query, market_type)
