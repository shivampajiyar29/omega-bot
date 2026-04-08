#!/usr/bin/env bash
# ============================================================
# OmegaBot Dev Script — fast startup with hot reload
# Starts only databases in Docker, runs API and web locally
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; NC='\033[0m'

echo -e "${CYAN}OmegaBot Dev Mode${NC}"
echo "━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"

# Check .env
[[ -f .env ]] || { cp .env.example .env; echo -e "${YELLOW}Created .env from .env.example${NC}"; }

# ─── Start infrastructure only ───────────────────────────────────────────────
echo -e "\n${YELLOW}Starting databases…${NC}"
docker compose up -d postgres redis timescaledb
echo "  Waiting for Postgres…"
until docker compose exec -T postgres pg_isready -U omegabot &>/dev/null; do sleep 1; done
echo -e "  ${GREEN}✓ Postgres ready${NC}"

# ─── Run migrations ───────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Applying migrations…${NC}"
cd apps/api
if [[ ! -d .venv ]]; then
    echo "  Creating Python venv…"
    python3 -m venv .venv
    .venv/bin/pip install --quiet -r requirements.txt
    echo -e "  ${GREEN}✓ venv created${NC}"
fi
source .venv/bin/activate
DATABASE_URL="$(grep DATABASE_URL ../../.env | cut -d= -f2-)" \
    alembic upgrade head 2>&1 | grep -v "^INFO\|^$" || true
echo -e "  ${GREEN}✓ Migrations done${NC}"
cd ../..

# ─── Start API in background ──────────────────────────────────────────────────
echo -e "\n${YELLOW}Starting API (uvicorn)…${NC}"
cd apps/api
source .venv/bin/activate
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload &
API_PID=$!
cd ../..
echo -e "  ${GREEN}✓ API: http://localhost:8000${NC}"
echo -e "  ${GREEN}  Docs: http://localhost:8000/docs${NC}"

# ─── Start Frontend ───────────────────────────────────────────────────────────
echo -e "\n${YELLOW}Starting Next.js dev server…${NC}"
cd apps/web
if [[ ! -d node_modules ]]; then
    echo "  Installing npm packages…"
    npm install --silent
fi
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev &
WEB_PID=$!
cd ../..
echo -e "  ${GREEN}✓ Web: http://localhost:3000${NC}"

echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"
echo -e "  ✅  Dev environment running!${NC}"
echo -e "  Dashboard : ${CYAN}http://localhost:3000${NC}"
echo -e "  API Docs  : ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo "  Press Ctrl+C to stop all services"
echo ""

# ─── Wait and cleanup ─────────────────────────────────────────────────────────
cleanup() {
    echo -e "\n${YELLOW}Stopping dev servers…${NC}"
    kill $API_PID $WEB_PID 2>/dev/null || true
    docker compose stop postgres redis timescaledb
    echo -e "${GREEN}Stopped.${NC}"
}
trap cleanup EXIT INT TERM
wait
