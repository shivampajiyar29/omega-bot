"""
Seed script — populates the database with default data.
Run once after first migration:
  cd apps/api && python -m app.scripts.seed_data
Or via: make seed
"""
import asyncio
import logging
import uuid
from datetime import datetime

from sqlalchemy import select

logging.basicConfig(level=logging.INFO)
log = logging.getLogger("seed")


async def seed():
    from app.core.database import AsyncSessionLocal, init_db
    from app.models.models import (
        BrokerConnector, MarketDataConnector, Watchlist, WatchlistSymbol,
        Strategy, EnabledModule, AppSetting, RiskProfile, ConnectorStatus,
        TradingMode, MarketType,
    )

    await init_db()

    async with AsyncSessionLocal() as db:

        # ── Broker Connectors ─────────────────────────────────────────────────
        brokers = [
            {"name": "mock",     "display_name": "Mock Broker (Paper)",   "adapter_class": "app.adapters.broker.mock_broker.MockBrokerAdapter",    "is_default": True,  "trading_mode": "paper", "market_types": ["equity","crypto"]},
            {"name": "groww",    "display_name": "Groww",                  "adapter_class": "app.adapters.broker.groww.GrowwBrokerAdapter",          "is_default": False, "trading_mode": "live",  "market_types": ["equity"]},
            {"name": "zerodha",  "display_name": "Zerodha (Kite)",         "adapter_class": "app.adapters.broker.zerodha.ZerodhaBrokerAdapter",     "is_default": False, "trading_mode": "live",  "market_types": ["equity","futures","options"]},
            {"name": "angel_one","display_name": "Angel One",              "adapter_class": "app.adapters.broker.angel_one.AngelOneBrokerAdapter",  "is_default": False, "trading_mode": "live",  "market_types": ["equity","futures"]},
            {"name": "dhan",     "display_name": "Dhan",                   "adapter_class": "app.adapters.broker.dhan.DhanBrokerAdapter",           "is_default": False, "trading_mode": "live",  "market_types": ["equity","futures"]},
            {"name": "upstox",   "display_name": "Upstox",                 "adapter_class": "app.adapters.broker.upstox.UpstoxBrokerAdapter",       "is_default": False, "trading_mode": "live",  "market_types": ["equity","futures"]},
            {"name": "binance",  "display_name": "Binance",                "adapter_class": "app.adapters.broker.binance.BinanceBrokerAdapter",     "is_default": False, "trading_mode": "live",  "market_types": ["crypto"]},
            {"name": "alpaca",   "display_name": "Alpaca (US Equities)",   "adapter_class": "app.adapters.broker.alpaca.AlpacaBrokerAdapter",       "is_default": False, "trading_mode": "paper", "market_types": ["equity"]},
        ]
        for b in brokers:
            existing = await db.execute(select(BrokerConnector).where(BrokerConnector.name == b["name"]))
            if not existing.scalar_one_or_none():
                conn = BrokerConnector(
                    id=str(uuid.uuid4()),
                    name=b["name"], display_name=b["display_name"],
                    adapter_class=b["adapter_class"],
                    status=ConnectorStatus.DISCONNECTED,
                    enabled=(b["name"] == "mock"),
                    is_default=b["is_default"],
                    trading_mode=b["trading_mode"],
                    market_types=b["market_types"],
                    config={},
                )
                db.add(conn)
                log.info(f"  + broker: {b['display_name']}")

        # ── Market Data Connectors ────────────────────────────────────────────
        md_connectors = [
            {"name": "mock",     "display_name": "Mock Data Generator",    "adapter_class": "app.adapters.marketdata.mock_data.MockMarketDataAdapter",       "markets": ["equity","crypto","futures"]},
            {"name": "binance",  "display_name": "Binance (crypto OHLCV)", "adapter_class": "app.adapters.marketdata.mock_data.MockMarketDataAdapter",       "markets": ["crypto"]},
            {"name": "influxdb", "display_name": "InfluxDB (time-series)", "adapter_class": "app.adapters.marketdata.influxdb_adapter.InfluxDBMarketDataAdapter", "markets": ["equity","crypto"]},
        ]
        for m in md_connectors:
            existing = await db.execute(select(MarketDataConnector).where(MarketDataConnector.name == m["name"]))
            if not existing.scalar_one_or_none():
                conn = MarketDataConnector(
                    id=str(uuid.uuid4()),
                    name=m["name"], display_name=m["display_name"],
                    adapter_class=m["adapter_class"],
                    status=ConnectorStatus.DISCONNECTED,
                    enabled=(m["name"] == "mock"),
                    supported_markets=m["markets"],
                    config={},
                )
                db.add(conn)
                log.info(f"  + marketdata: {m['display_name']}")

        # ── Default Watchlist ─────────────────────────────────────────────────
        wl = await db.execute(select(Watchlist).where(Watchlist.is_default == True))
        if not wl.scalar_one_or_none():
            wl_obj = Watchlist(id=str(uuid.uuid4()), name="My Watchlist", is_default=True)
            db.add(wl_obj)
            await db.flush()
            symbols = [
                ("RELIANCE", "NSE", "equity"), ("TCS", "NSE", "equity"),
                ("INFY", "NSE", "equity"), ("HDFC", "NSE", "equity"),
                ("BAJFINANCE", "NSE", "equity"), ("WIPRO", "NSE", "equity"),
                ("NIFTY50", "NSE", "equity"), ("BANKNIFTY", "NSE", "futures"),
                ("BTCUSDT", "BINANCE", "crypto"), ("ETHUSDT", "BINANCE", "crypto"),
            ]
            for sym, exc, mtype in symbols:
                db.add(WatchlistSymbol(
                    id=str(uuid.uuid4()), watchlist_id=wl_obj.id,
                    symbol=sym, exchange=exc, market_type=mtype,
                ))
            log.info(f"  + watchlist: My Watchlist ({len(symbols)} symbols)")

        # ── Sample Strategies ─────────────────────────────────────────────────
        from app.strategy.dsl import SAMPLE_STRATEGIES
        existing_strats = await db.execute(select(Strategy))
        existing_names = {s.name for s in existing_strats.scalars().all()}

        strategy_defs = [
            ("EMA Crossover (9/21)",       "equity", SAMPLE_STRATEGIES.get("ema_crossover", {}),  ["trend","momentum"]),
            ("RSI Breakout",               "equity", SAMPLE_STRATEGIES.get("rsi_breakout", {}),    ["momentum","oscillator"]),
            ("MACD Momentum",             "equity", SAMPLE_STRATEGIES.get("macd_momentum", {}),   ["momentum","macd"]),
            ("Crypto EMA + RSI",          "crypto", SAMPLE_STRATEGIES.get("ema_crossover", {}),   ["crypto","trend"]),
        ]
        for name, mtype, dsl, tags in strategy_defs:
            if name not in existing_names and dsl:
                db.add(Strategy(
                    id=str(uuid.uuid4()), name=name,
                    description=f"Sample {mtype} strategy — {name}",
                    market_type=mtype, dsl=dsl, is_active=True, tags=tags,
                ))
                log.info(f"  + strategy: {name}")

        # ── Default Risk Profile ──────────────────────────────────────────────
        from app.models.models import RiskProfile
        rp_existing = await db.execute(select(RiskProfile).where(RiskProfile.name == "Default"))
        if not rp_existing.scalar_one_or_none():
            db.add(RiskProfile(
                id=str(uuid.uuid4()), name="Default",
                max_daily_loss=5000.0, max_trade_loss=1000.0,
                max_open_positions=10, max_order_value=50000.0,
                max_margin_pct=80.0,
                allowed_hours_start="09:15", allowed_hours_end="15:30",
                symbol_blacklist=[], is_active=True,
            ))
            log.info("  + risk profile: Default")

        # ── Enabled Modules ───────────────────────────────────────────────────
        modules = [
            ("paper_trading",    True,  "Paper trading engine with mock fills"),
            ("backtester",       True,  "Historical strategy backtesting"),
            ("ai_assistant",     True,  "AI-powered strategy assistant"),
            ("screener",         True,  "Multi-symbol signal screener"),
            ("trade_journal",    True,  "Personal trade journal"),
            ("custom_indicators",True,  "Custom Python indicator builder"),
            ("notifications",    False, "Telegram / webhook notifications"),
            ("live_trading",     False, "Live broker order execution"),
        ]
        for mname, enabled, desc in modules:
            existing = await db.execute(select(EnabledModule).where(EnabledModule.name == mname))
            if not existing.scalar_one_or_none():
                db.add(EnabledModule(name=mname, enabled=enabled, description=desc, config={}))

        # ── App Settings ──────────────────────────────────────────────────────
        default_settings = [
            ("trading_mode",       "paper",    "Active trading mode: paper | live"),
            ("default_broker",     "mock",     "Active broker connector name"),
            ("default_capital",    "100000",   "Default paper trading capital in INR"),
            ("theme",              "dark",     "UI theme: dark | light"),
            ("default_timeframe",  "15m",      "Default chart timeframe"),
            ("auto_backtest",      "false",    "Auto-run backtest on strategy save"),
            ("notifications_enabled","false",  "Enable Telegram notifications"),
            ("ai_signals_enabled", "true",     "Show AI signals in charts"),
        ]
        for key, val, desc in default_settings:
            existing = await db.execute(select(AppSetting).where(AppSetting.key == key))
            if not existing.scalar_one_or_none():
                db.add(AppSetting(key=key, value=val, description=desc))

        await db.commit()
        log.info("\n✅ Seed complete — database ready")


if __name__ == "__main__":
    asyncio.run(seed())
