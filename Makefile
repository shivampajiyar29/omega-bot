# ============================================================
# OmegaBot Makefile — Personal Trading Platform
# ============================================================
.PHONY: help setup start start-dev stop restart restart-api logs logs-api \
        logs-web shell-api shell-web shell-db migrate migrate-create \
        migrate-down test test-unit test-integration test-coverage lint \
        format backup restore update clean clean-all seed generate-mock \
        status build-prod deploy-prod

GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

help: ## Show this help
	@echo ""
	@echo "  $(CYAN)OmegaBot — Personal Trading Platform$(RESET)"
	@echo ""
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-22s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ─── Setup ───────────────────────────────────────────────────────────────────
setup: ## First-time setup: copy .env, build images, init DB
	@echo "$(YELLOW)Setting up OmegaBot...$(RESET)"
	@[ -f .env ] || (cp .env.example .env && echo "  → .env created. Edit it before going live.")
	@docker compose build
	@docker compose up -d postgres redis timescaledb
	@echo "  → Waiting for databases..."
	@sleep 8
	@docker compose run --rm api alembic upgrade head
	@echo "$(GREEN)✓ Setup complete. Run 'make seed && make start'$(RESET)"

# ─── Run ─────────────────────────────────────────────────────────────────────
start: ## Start all services
	@docker compose up -d
	@echo "$(GREEN)✓ Running at http://localhost:3000$(RESET)"
	@echo "  API docs: http://localhost:8000/docs"

start-dev: ## Start with all logs visible (Ctrl+C to stop)
	docker compose up

start-local: ## Start databases in Docker, run API+web locally
	@./scripts/dev.sh

stop: ## Stop all services
	docker compose stop

restart: ## Restart all services
	docker compose restart

restart-api: ## Restart only API + worker
	docker compose restart api worker

# ─── Logs ────────────────────────────────────────────────────────────────────
logs: ## Follow all service logs
	docker compose logs -f

logs-api: ## Follow API logs only
	docker compose logs -f api

logs-web: ## Follow frontend logs only
	docker compose logs -f web

logs-worker: ## Follow worker logs only
	docker compose logs -f worker

# ─── Shells ──────────────────────────────────────────────────────────────────
shell-api: ## Open shell in API container
	docker compose exec api bash

shell-web: ## Open shell in web container
	docker compose exec web sh

shell-db: ## Open psql prompt
	docker compose exec postgres psql -U omegabot omegabot

shell-redis: ## Open redis-cli
	docker compose exec redis redis-cli -a redis_secret

# ─── Database ────────────────────────────────────────────────────────────────
migrate: ## Run pending migrations
	docker compose run --rm api alembic upgrade head

migrate-create: ## Create new migration (MSG="description")
	docker compose run --rm api alembic revision --autogenerate -m "$(MSG)"

migrate-down: ## Rollback one migration
	docker compose run --rm api alembic downgrade -1

migrate-history: ## Show migration history
	docker compose run --rm api alembic history

migrate-current: ## Show current migration
	docker compose run --rm api alembic current

# ─── Data ────────────────────────────────────────────────────────────────────
seed: ## Load sample strategies, watchlist, connectors
	docker compose run --rm api python -m app.scripts.seed_data

generate-mock: ## Generate synthetic OHLCV CSV data for backtesting
	docker compose run --rm api python -m app.scripts.generate_mock_data

# ─── Testing ─────────────────────────────────────────────────────────────────
test: ## Run all tests
	docker compose run --rm api pytest tests/ -v

test-unit: ## Run unit tests (no DB needed)
	docker compose run --rm api pytest tests/test_mock_broker.py tests/test_backtest_engine.py tests/test_dsl_evaluator.py tests/test_strategies.py tests/test_execution.py tests/test_schemas.py -v

test-integration: ## Run integration tests (needs running DB)
	docker compose run --rm api pytest tests/test_integration.py tests/test_strategy_service.py -v

test-coverage: ## Run tests with HTML coverage report
	docker compose run --rm api pytest tests/ --cov=app --cov-report=html
	@echo "Coverage report: apps/api/htmlcov/index.html"

test-watch: ## Run tests in watch mode
	docker compose run --rm api pytest-watch tests/

# ─── Code Quality ────────────────────────────────────────────────────────────
lint: ## Run linters (ruff + mypy)
	docker compose run --rm api ruff check app/ tests/
	docker compose run --rm api mypy app/ --ignore-missing-imports

format: ## Auto-format code with ruff
	docker compose run --rm api ruff format app/ tests/

typecheck: ## Run mypy type checker only
	docker compose run --rm api mypy app/ --ignore-missing-imports

# ─── Backup & Restore ─────────────────────────────────────────────────────────
backup: ## Backup database + strategies
	@./scripts/backup.sh

restore: ## Restore from backup (FILE=backups/omegabot_YYYYMMDD.tar.gz)
	@[ -f "$(FILE)" ] || (echo "Usage: make restore FILE=backups/omegabot_YYYYMMDD.tar.gz" && exit 1)
	@gunzip -c $(FILE) | docker compose exec -T postgres psql -U omegabot omegabot
	@echo "$(GREEN)✓ Restored$(RESET)"

# ─── Update ──────────────────────────────────────────────────────────────────
update: ## Pull latest + backup + rebuild + migrate + restart
	@./scripts/update.sh

# ─── Production ──────────────────────────────────────────────────────────────
build-prod: ## Build production Docker images
	docker compose -f infra/docker-compose.prod.yml build

deploy-prod: ## Deploy production stack
	docker compose -f infra/docker-compose.prod.yml up -d
	@echo "$(GREEN)✓ Production stack started$(RESET)"

# ─── Cleanup ─────────────────────────────────────────────────────────────────
clean: ## Stop and remove containers (data preserved)
	docker compose down

clean-all: ## DANGER: Remove everything including data volumes
	docker compose down -v
	@echo "$(YELLOW)Warning: All data volumes removed$(RESET)"

clean-pyc: ## Remove Python cache files
	find apps/api -type f -name "*.pyc" -delete
	find apps/api -type d -name "__pycache__" -delete

# ─── Info ─────────────────────────────────────────────────────────────────────
status: ## Show service status and URLs
	@docker compose ps
	@echo ""
	@echo "  $(CYAN)Web     :$(RESET) http://localhost:3000"
	@echo "  $(CYAN)API     :$(RESET) http://localhost:8000"
	@echo "  $(CYAN)API Docs:$(RESET) http://localhost:8000/docs"
	@echo ""
