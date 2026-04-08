# OmegaBot — Supplementary Files (Patch v1.1)

This archive contains all files that were added **after** the main `omegabot_v1_complete.tar.gz`.

## How to apply

```bash
# Extract main archive first
tar -xzf omegabot_v1_complete.tar.gz

# Then extract this patch on top
tar -xzf omegabot_patch_v1.1.tar.gz

# Result: fully merged project
```

---

## What's new in this patch

### New broker adapters
| File | Broker |
|---|---|
| `apps/api/app/adapters/broker/upstox.py` | Upstox Pro API (NSE/BSE) |
| `apps/api/app/adapters/broker/binance.py` | Already in main archive |
| `apps/api/app/adapters/broker/angel_one.py` | Already in main archive |
| `apps/api/app/adapters/broker/dhan.py` | Already in main archive |

### New API schemas
- `apps/api/app/schemas/schemas.py` — Full Pydantic v2 request/response validation for all entities (Strategy, Bot, Order, Backtest, Risk, Webhook). Separates API contracts from SQLAlchemy models.

### New business logic layer
- `apps/api/app/services/strategy_service.py` — Strategy CRUD with version management, running-bot safety check before delete, sample loader, version restore.

### New UI components
| File | Component |
|---|---|
| `apps/web/src/components/ui/button.tsx` | Button with variants (primary, danger, ghost, outline) + loading spinner |
| `apps/web/src/components/ui/card.tsx` | Card, CardHeader, StatCard |
| `apps/web/src/components/ui/index.tsx` | Badge, Input, Select, Table\<T\>, Toggle |
| `apps/web/src/components/charts/CandlestickChart.tsx` | Reusable candlestick wrapper with EMA overlays, volume, crosshair |
| `apps/web/src/components/trading/index.tsx` | BotCard (start/pause/stop), QuickOrder form |
| `apps/web/src/components/risk/RiskMeter.tsx` | Animated risk progress bar, RiskDashboard grid |

### Production infrastructure
| File | Purpose |
|---|---|
| `apps/api/Dockerfile.prod` | Multi-stage build, non-root user, healthcheck |
| `apps/web/Dockerfile.prod` | Next.js standalone build, minimal runtime |
| `infra/docker-compose.prod.yml` | Production stack: internal network, memory limits, always-restart |
| `infra/nginx/nginx.prod.conf` | HTTPS, rate limiting, security headers, WebSocket |

### Scripts & CI
| File | Purpose |
|---|---|
| `scripts/install.sh` | One-command fresh server setup |
| `scripts/dev.sh` | Local dev: databases in Docker, API + web native with hot reload |
| `.github/workflows/ci.yml` | GitHub Actions: backend tests, frontend build, Docker build check |

---

## Registering Upstox in the connector registry

After extracting, add Upstox to `apps/api/app/connectors/registry.py`:

```python
_try_register_broker("upstox", "app.adapters.broker.upstox", "UpstoxBrokerAdapter")
```

## Using the new schemas

The schemas in `app/schemas/schemas.py` can replace bare `dict` in endpoint responses. Example update to `strategies.py`:

```python
from app.schemas.schemas import StrategyCreateSchema, StrategyResponseSchema

@router.post("/", response_model=StrategyResponseSchema, status_code=201)
async def create_strategy(data: StrategyCreateSchema, db: AsyncSession = Depends(get_db)):
    svc = StrategyService(db)
    strategy = await svc.create(
        name=data.name, dsl=data.dsl,
        description=data.description or "",
        market_type=data.market_type,
        tags=data.tags,
    )
    await db.commit()
    return strategy
```

## Using the BotCard component

```tsx
import { BotCard } from "@/components/trading";

<BotCard
  bot={{ id: "1", name: "EMA Bot", symbol: "RELIANCE", status: "running", pnl: 2840 }}
  onPause={(id) => api.pauseBot(id)}
  onStop={(id) => api.stopBot(id)}
/>
```

## Using the CandlestickChart component

```tsx
import { CandlestickChart } from "@/components/charts/CandlestickChart";

<CandlestickChart
  data={ohlcvData}
  height={400}
  showEMA={[
    { period: 9, color: "#4a9eff" },
    { period: 21, color: "#ffb347" },
  ]}
  onCrosshairMove={(bar) => setCurrentBar(bar)}
/>
```
