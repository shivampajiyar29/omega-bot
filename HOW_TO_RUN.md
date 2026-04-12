# How to Run OmegaBot

OmegaBot is a **FastAPI (Python) + Next.js** platform. The original Node.js instructions were wrong — ignore them.

---

## Prerequisites

- Docker Desktop (includes Docker Compose)
- Git

That's it. No Python or Node.js installation needed locally.

---

## Quick Start (Docker — one command)

```bash
# 1. Clone
git clone https://github.com/shivampajiyar29/omega-bot.git
cd omega-bot

# 2. Configure (defaults work without editing)
cp .env.example .env

# 3. Start everything
docker compose up --build

# 4. Open browser
#    Dashboard:  http://localhost:13000
#    API Docs:   http://localhost:18000/docs
#    Health:     http://localhost:18000/health  →  {"status":"ok"}
```

The first build takes 2–4 minutes (downloads images, installs packages).

---

## With AI Engine (XGBoost + LSTM signals)

```bash
docker compose --profile ai up --build
# AI Engine URL: http://localhost:8001/health
# Note: First startup trains ML models — takes ~60–90 seconds
```

---

## With Make (recommended)

```bash
make setup       # copies .env, builds images
make seed        # loads sample strategies + watchlist
make start       # starts all services (no AI)
make start-all   # starts everything including AI
make logs        # follow all logs
make status      # show URLs and service health
make stop        # stop all
```

---

## Local Development (no Docker)

```bash
# Databases only in Docker
docker compose up -d postgres redis

# Backend (Terminal 1)
cd apps/api
python3 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
DATABASE_URL="postgresql+asyncpg://omegabot:omegabot_secret@localhost:5432/omegabot" \
REDIS_URL="redis://:redis_secret@localhost:6379/0" \
  uvicorn app.main:app --port 8000 --reload

# Frontend (Terminal 2)
cd apps/web
npm install
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev
# Open: http://localhost:3000

# AI Engine (Terminal 3, optional)
cd ai_engine
pip install -r requirements.txt
uvicorn ai_engine.main:app --port 8001 --reload
# First run trains models (~60s)
```

---

## Service URLs

| Service       | URL                                   |
|---------------|---------------------------------------|
| Dashboard     | http://localhost:13000                |
| API Docs      | http://localhost:18000/docs           |
| Health Check  | http://localhost:18000/health         |
| API (dev)     | http://localhost:8000/docs            |
| AI Engine     | http://localhost:8001/health          |
| PostgreSQL    | localhost:5432                        |
| Redis         | localhost:6379                        |

---

## Tech Stack

| Layer     | Technology                                                          |
|-----------|---------------------------------------------------------------------|
| Backend   | Python 3.11, FastAPI, SQLAlchemy 2.0 async, Alembic, Celery       |
| Frontend  | Next.js 14, TypeScript, Tailwind CSS, Zustand, TanStack Query      |
| Database  | PostgreSQL 16 (primary), Redis 7 (cache/stream), SQLite (tests)    |
| AI/ML     | XGBoost, scikit-learn, feature engineering (32 indicators)         |
| Charts    | lightweight-charts (candlestick), Recharts (analytics)             |
| Brokers   | Mock, Groww, Zerodha, Angel One, Dhan, Upstox, Binance, Alpaca    |

---

## Troubleshooting

**API crashes on startup:**
```bash
docker compose logs api
# Most common: DB not ready yet — wait 10s and retry
docker compose restart api
```

**Port already in use:**
```bash
# Change ports in docker-compose.yml: "18000:8000" → "18001:8000"
```

**Database not initialized:**
```bash
docker compose run --rm api alembic upgrade head
docker compose run --rm api python -m app.scripts.seed_data
```

**AI Engine keeps restarting:**
```bash
docker compose logs ai_engine
# It takes 60-90s to train models on first boot — this is normal
```

**Reset everything:**
```bash
make clean-all   # removes containers and volumes
make setup && make start
```
