#!/usr/bin/env bash
# ============================================================
# OmegaBot — Fresh Server Install Script
# Tested on Ubuntu 22.04 LTS
# Usage: curl -fsSL https://raw.githubusercontent.com/.../install.sh | bash
#   OR:  ./scripts/install.sh
# ============================================================
set -euo pipefail

GREEN='\033[0;32m'; YELLOW='\033[0;33m'; CYAN='\033[0;36m'; RED='\033[0;31m'; NC='\033[0m'

step() { echo -e "\n${CYAN}━━━ $1 ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"; }
ok()   { echo -e "  ${GREEN}✓${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC}  $1"; }
die()  { echo -e "  ${RED}✗${NC} $1"; exit 1; }

echo -e "${GREEN}"
cat << 'BANNER'
  ___  _ __ ___   ___  __ _  __ _  __ _| |__   ___ | |_
 / _ \| '_ ` _ \ / _ \/ _` |/ _` |/ _` | '_ \ / _ \| __|
| (_) | | | | | |  __/ (_| | (_| | (_| | |_) | (_) | |_
 \___/|_| |_| |_|\___|\__, |\__,_|\__,_|_.__/ \___/ \__|
                       |___/  Personal Trading Platform
BANNER
echo -e "${NC}"

# ─── Check OS ────────────────────────────────────────────────────────────────
step "Checking system"
[[ "$(uname -s)" == "Linux" ]] || die "This script requires Linux (Ubuntu 22.04 recommended)"
ok "OS: $(lsb_release -d 2>/dev/null | cut -f2 || echo Linux)"

# ─── Install Docker ───────────────────────────────────────────────────────────
step "Installing Docker"
if command -v docker &>/dev/null; then
    ok "Docker already installed: $(docker --version)"
else
    curl -fsSL https://get.docker.com | sh
    sudo usermod -aG docker "$USER"
    ok "Docker installed"
    warn "You may need to log out and back in for Docker group permissions"
fi

if command -v docker compose &>/dev/null || docker compose version &>/dev/null 2>&1; then
    ok "Docker Compose available"
else
    die "Docker Compose not found. Install Docker Desktop or docker-compose-plugin"
fi

# ─── Install utilities ────────────────────────────────────────────────────────
step "Installing utilities"
sudo apt-get update -q
sudo apt-get install -y -q git make curl jq
ok "git, make, curl, jq installed"

# ─── Setup project ────────────────────────────────────────────────────────────
step "Setting up OmegaBot"

# Create .env if missing
if [[ ! -f .env ]]; then
    cp .env.example .env
    ok ".env created from .env.example"
    warn "Edit .env with your passwords before going live!"
    warn "  nano .env"
else
    ok ".env already exists"
fi

# Create data directories
mkdir -p data/csv backups logs
ok "Data directories created: data/csv, backups, logs"

# Make scripts executable
chmod +x scripts/*.sh 2>/dev/null || true
ok "Scripts made executable"

# ─── Build and start ──────────────────────────────────────────────────────────
step "Building Docker images (first time: 3–5 minutes)"
docker compose build
ok "Images built"

step "Starting databases"
docker compose up -d postgres redis timescaledb
echo -n "  Waiting for databases to be ready"
for i in {1..30}; do
    if docker compose exec -T postgres pg_isready -U omegabot &>/dev/null; then
        echo " ✓"
        break
    fi
    echo -n "."
    sleep 2
done

step "Running database migrations"
docker compose run --rm api alembic upgrade head
ok "Migrations applied"

step "Loading sample data"
docker compose run --rm api python -m app.scripts.seed_data
ok "Sample data loaded"

step "Starting all services"
docker compose up -d
ok "All services started"

# ─── Done ─────────────────────────────────────────────────────────────────────
echo ""
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo -e "${GREEN}  ✅  OmegaBot is running!${NC}"
echo -e "${GREEN}━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━${NC}"
echo ""
echo -e "  Dashboard : ${CYAN}http://localhost:3000${NC}"
echo -e "  API Docs  : ${CYAN}http://localhost:8000/docs${NC}"
echo ""
echo "  Useful commands:"
echo "    make logs          — follow logs"
echo "    make status        — show service status"
echo "    make stop          — stop all services"
echo "    make backup        — backup database"
echo ""
echo -e "  ${YELLOW}Next steps:${NC}"
echo "    1. Open http://localhost:3000"
echo "    2. Platform starts in PAPER mode — no real money"
echo "    3. Add broker keys in Settings when ready"
echo "    4. Read docs/INSTALL.md for VPS deployment"
echo ""
