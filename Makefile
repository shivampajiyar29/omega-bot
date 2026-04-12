.PHONY: help setup start start-all start-dev stop restart \
        logs logs-api logs-web logs-worker logs-ai \
        migrate migrate-create seed test test-unit test-ai \
        lint format clean clean-all status build-prod ai-start ai-stop

# ── Colors ────────────────────────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

help: ## Show this help
	@echo ""
	@echo "  $(CYAN)OmegaBot — Personal Trading Platform$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ── Setup & Start ─────────────────────────────────────────────────────────────
setup: ## First-time setup: copy .env, build images
	@[ -f .env ] || (cp .env.example .env && echo "$(YELLOW)→ .env created — edit it before going live$(RESET)")
	docker compose build
	@echo "$(GREEN)✓ Setup done. Run: make start$(RESET)"

start: ## Start core stack (no AI engine)
	docker compose up -d postgres redis api worker beat web
	@echo "$(GREEN)✓ Stack started"
	@echo "  Dashboard: http://localhost:13000"
	@echo "  API Docs:  http://localhost:18000/docs$(RESET)"

start-all: ## Start everything including AI Engine
	docker compose --profile ai up -d
	@echo "$(GREEN)✓ Full stack + AI Engine started (AI trains on first boot ~90s)$(RESET)"

start-dev: ## Start in foreground with logs
	docker compose up

stop: ## Stop all services
	docker compose down

restart: ## Restart API and worker
	docker compose restart api worker

# ── Logs ─────────────────────────────────────────────────────────────────────
logs: ## Follow all logs
	docker compose logs -f

logs-api: ## API logs only
	docker compose logs -f api

logs-web: ## Web logs only
	docker compose logs -f web

logs-worker: ## Worker logs only
	docker compose logs -f worker

logs-ai: ## AI Engine logs
	docker compose logs -f ai_engine

# ── Database ──────────────────────────────────────────────────────────────────
migrate: ## Run Alembic migrations
	docker compose run --rm api alembic upgrade head

migrate-create: ## Create new migration (MSG="description")
	docker compose run --rm api alembic revision --autogenerate -m "$(MSG)"

seed: ## Load sample data (strategies, watchlist, connectors)
	docker compose run --rm api python -m app.scripts.seed_data

# ── Testing ───────────────────────────────────────────────────────────────────
test: ## Run all tests
	docker compose run --rm api pytest tests/ -v

test-unit: ## Run fast unit tests
	docker compose run --rm api pytest tests/ -v -m "not slow"

test-ai: ## Run AI engine tests
	cd ai_engine && pip install -q pytest && python -m pytest tests/ -v

# ── Code Quality ──────────────────────────────────────────────────────────────
lint: ## Lint with ruff
	docker compose run --rm api ruff check app/

format: ## Format code
	docker compose run --rm api ruff format app/

# ── AI Engine ─────────────────────────────────────────────────────────────────
ai-start: ## Start AI Engine in Docker
	docker compose --profile ai up -d ai_engine
	@echo "$(GREEN)✓ AI Engine started on port 8001 (training models ~90s)$(RESET)"

ai-stop: ## Stop AI Engine
	docker compose stop ai_engine

ai-health: ## Check AI Engine health
	@curl -sf http://localhost:8001/health | python3 -m json.tool || echo "$(YELLOW)AI Engine not running$(RESET)"

# ── Status ────────────────────────────────────────────────────────────────────
status: ## Show service status and URLs
	@docker compose ps
	@echo ""
	@echo "  Dashboard:  http://localhost:13000"
	@echo "  API Docs:   http://localhost:18000/docs"
	@echo "  Health:     http://localhost:18000/health"
	@echo "  AI Engine:  http://localhost:8001/health"

# ── Production ────────────────────────────────────────────────────────────────
build-prod: ## Build production images
	docker compose -f infra/docker-compose.prod.yml build

# ── Cleanup ───────────────────────────────────────────────────────────────────
clean: ## Stop containers (data preserved)
	docker compose down

clean-all: ## DANGER: Remove containers + volumes
	docker compose down -v

clean-pyc: ## Remove Python cache files
	find . -name "*.pyc" -delete
	find . -type d -name "__pycache__" -delete
