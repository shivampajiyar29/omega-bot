# OmegaBot — Personal Algorithmic Trading Platform

> Your private, self-hosted trading workstation. Run strategies, backtest, paper trade, and go live — all from a single clean dashboard.

---

## What Is This?

OmegaBot is a **single-user, self-hosted** algorithmic trading platform built for personal use.
It is **not** a SaaS product — there is no multi-tenancy, no billing, no accounts.
You run it on your own machine or VPS, and it's yours.

### Capabilities

| Feature | Status |
|---|---|
| Dashboard with market overview, P&L, bots | ✅ |
| Strategy Builder (wizard + DSL JSON) | ✅ |
| Backtesting engine | ✅ |
| Paper trading (mock broker) | ✅ |
| Live trading (broker adapters) | 🔌 Pluggable |
| Risk management & kill switch | ✅ |
| AI strategy assistant | 🔌 Optional |
| Module enable/disable | ✅ |
| NSE/BSE/Crypto/Forex ready architecture | ✅ |

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Git

### 1. Clone & setup
```bash
git clone https://github.com/you/omegabot.git
cd omegabot
make setup
```

### 2. Start
```bash
make start
```

Open:
- **Dashboard**: http://localhost:3000
- **API Docs**: http://localhost:8000/docs

### 3. First run
The platform starts in **Paper mode** with the **Mock broker** connected.
No real money, no API keys needed to get started.

---

## Architecture

```
omegabot/
├── apps/
│   ├── web/          # Next.js 14 + TypeScript + Tailwind frontend
│   ├── api/          # FastAPI + SQLAlchemy Python backend
│   └── worker/       # Celery background job worker
├── docs/             # Documentation and UI mockup prompts
├── infra/            # Nginx, Postgres, Redis configs
├── scripts/          # Backup, restore, update scripts
└── tests/            # Unit, integration, e2e tests
```

### Tech Stack

**Frontend**
- Next.js 14, TypeScript, Tailwind CSS
- Zustand (state), TanStack Query (server state)
- Lightweight Charts (candlestick), Recharts (analytics)
- IBM Plex Mono + Syne fonts

**Backend**
- FastAPI (Python 3.11+), SQLAlchemy 2.0 (async)
- Alembic migrations, Pydantic v2
- Celery + Redis for background jobs

**Storage**
- PostgreSQL — app data (strategies, bots, orders, etc.)
- TimescaleDB — time-series OHLCV price data
- Redis — cache, pub/sub, task queue

---

## Broker Connectors

OmegaBot uses an **adapter-based** connector system.
Each broker is a separate Python class that implements `BaseBrokerAdapter`.

| Connector | Status | Notes |
|---|---|---|
| Mock Broker | ✅ Built-in | Default for paper trading |
| CSV Data | ✅ Built-in | Load historical data from CSV |
| Zerodha / Kite | 🔧 Add keys in .env | NSE/BSE equities |
| Angel One | 🔧 Add keys in .env | NSE/BSE equities |
| Dhan | 🔧 Add keys in .env | NSE/BSE equities |
| Alpaca | 🔧 Add keys in .env | US equities |
| Binance | 🔧 Add keys in .env | Crypto |
| IBKR | 🔧 Configure TWS | Global markets |

To add a new broker:
1. Create `apps/api/app/adapters/broker/your_broker.py`
2. Subclass `BaseBrokerAdapter` and implement all methods
3. Register in `apps/api/app/connectors/registry.py`
4. Enable from the Connectors page

---

## Strategy DSL

Strategies are defined as JSON using the OmegaBot DSL format.

```json
{
  "version": "1.0",
  "name": "EMA 9/21 Crossover",
  "timeframe": "15m",
  "indicators": [
    { "id": "ema9",  "type": "ema", "params": { "period": 9  } },
    { "id": "ema21", "type": "ema", "params": { "period": 21 } }
  ],
  "entry": {
    "long": {
      "logic": "and",
      "conditions": [
        { "left": { "indicator_id": "ema9" }, "operator": "crosses_above", "right": { "indicator_id": "ema21" } }
      ]
    }
  },
  "exits": [
    { "type": "fixed_stop", "value": 1.5, "unit": "pct" }
  ],
  "sizing": { "method": "fixed_value", "value": 25000 }
}
```

Strategies can also be created from the visual wizard or with the AI assistant.

---

## Risk Management

OmegaBot has built-in guardrails:

- **Max daily loss** — bot stops when daily P&L hits threshold
- **Max trade loss** — stops individual trades at defined loss
- **Kill switch** — stops ALL bots instantly from topbar
- **Margin guard** — prevents over-leveraging
- **Trading hours** — only trades in defined market windows
- **Symbol blacklist** — never trade specific symbols
- **Duplicate order protection** — prevents double-entry

All configurable in Settings → Risk Defaults or per-bot.

---

## Module System

Enable only what you need. Disabled modules are hidden and dormant.

**Always on**: Dashboard, Orders, Positions, Logs, Connectors, Settings

**Toggle on/off**: Backtester, Paper Trading, Live Trading, Risk Center, Portfolio, AI Assistant, Options Analytics, Scanner, Screener, Trade Journal, Webhook Automation

---

## Useful Commands

```bash
make start          # Start all services
make stop           # Stop all services
make logs           # Follow all logs
make migrate        # Run DB migrations
make backup         # Backup database
make update         # Pull latest + rebuild
make test           # Run tests
make shell-api      # Shell into API container
make shell-db       # psql shell
make seed           # Load sample data
```

---

## Deployment

### Local (default)
```bash
make start
```

### VPS (Ubuntu 22.04)
```bash
# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Clone and start
git clone https://github.com/you/omegabot.git
cd omegabot
cp .env.example .env
nano .env  # Edit your settings
make setup
make start
```

For HTTPS on a VPS, uncomment and configure the Nginx SSL section in `infra/nginx/nginx.conf`.

---

## UI Design

All design mockup prompts (for Midjourney / DALL-E) are in: `docs/UI_MOCKUP_PROMPTS.md`

Color palette:
- Background: `#0a0b0e`
- Cards: `#16191f`
- Green (profit): `#00d4a0`
- Red (loss): `#ff4757`
- Blue (active): `#4a9eff`

Fonts: IBM Plex Mono (numbers) + Syne (UI labels)

---

## Roadmap

- [ ] Options chain viewer with Greeks
- [ ] Advanced backtesting optimizer (parameter sweep)
- [ ] Trade journal with image uploads
- [ ] TradingView webhook receiver
- [ ] Mobile PWA companion
- [ ] Monte Carlo analysis
- [ ] Strategy comparison report
- [ ] Tax export (P&L by FY)

---

## License

Personal use only. Not for redistribution or commercial use.
