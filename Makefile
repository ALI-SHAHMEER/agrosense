# ============================================================
# AgroSense Makefile
# Run `make help` to see all available commands
# ============================================================

.PHONY: help setup dev stop logs clean migrate rollback test lint \
        gee-auth gcp-auth infra-init infra-apply deploy build push

# ── Colours ──────────────────────────────────────────────────
GREEN  := \033[0;32m
YELLOW := \033[0;33m
CYAN   := \033[0;36m
RESET  := \033[0m

# ── Variables ────────────────────────────────────────────────
COMPOSE        := docker compose
GCP_PROJECT    ?= $(shell grep GCP_PROJECT_ID .env | cut -d '=' -f2)
GCP_REGION     ?= us-central1
API_IMAGE      := gcr.io/$(GCP_PROJECT)/agrosense-api
DASHBOARD_IMAGE := gcr.io/$(GCP_PROJECT)/agrosense-dashboard

help: ## Show this help message
	@echo ""
	@echo "$(CYAN)AgroSense — Available Commands$(RESET)"
	@echo "────────────────────────────────────────"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | \
		awk 'BEGIN {FS = ":.*?## "}; {printf "  $(GREEN)%-20s$(RESET) %s\n", $$1, $$2}'
	@echo ""

# ── Local Development ─────────────────────────────────────────
setup: ## First-time setup: copy .env and create required folders
	@echo "$(CYAN)Setting up AgroSense...$(RESET)"
	@[ -f .env ] || (cp .env.example .env && echo "  ✓ Created .env — fill in credentials before make dev")
	@mkdir -p infrastructure/keys services/ml_models/saved_models
	@echo "$(GREEN)✓ Setup complete!$(RESET)"
	@echo ""
	@echo "  1. Edit credentials:  nano .env"
	@echo "  2. Start services:    make dev"
	@echo ""
	@echo "  Python/Node deps install automatically inside Docker."

setup-local: ## Install deps on host machine (for IDE autocomplete only)
	@echo "$(CYAN)Installing host Python deps for IDE support...$(RESET)"
	@command -v pip3 >/dev/null 2>&1 || (echo "pip3 not found" && exit 1)
	pip3 install -r services/api/requirements.txt
	pip3 install -r services/gee_pipeline/requirements.txt
	@command -v npm >/dev/null 2>&1 && (cd services/dashboard && npm install) || true
	@echo "$(GREEN)✓ Local deps installed$(RESET)"

dev: ## Start all services locally with hot-reload
	@echo "$(CYAN)Starting AgroSense dev stack...$(RESET)"
	$(COMPOSE) up --build -d
	@echo ""
	@echo "$(GREEN)✓ Services running:$(RESET)"
	@echo "  API:        http://localhost:8000"
	@echo "  API Docs:   http://localhost:8000/docs"
	@echo "  Dashboard:  http://localhost:3000"
	@echo "  DB:         localhost:5432"

stop: ## Stop all running services
	$(COMPOSE) down

logs: ## Tail logs for all services (Ctrl+C to exit)
	$(COMPOSE) logs -f

logs-api: ## Tail API logs only
	$(COMPOSE) logs -f api

logs-db: ## Tail database logs only
	$(COMPOSE) logs -f db

clean: ## Stop services and remove volumes (WARNING: deletes local DB data)
	@echo "$(YELLOW)Warning: This will delete all local database data.$(RESET)"
	@read -p "Are you sure? [y/N] " confirm && [ "$$confirm" = "y" ]
	$(COMPOSE) down -v --remove-orphans

restart-api: ## Restart only the API service
	$(COMPOSE) restart api

tools: ## Start dev tools (Adminer DB UI at :8080)
	$(COMPOSE) --profile tools up -d adminer

# ── Database ──────────────────────────────────────────────────
migrate: ## Run database migrations
	@echo "$(CYAN)Running migrations...$(RESET)"
	$(COMPOSE) exec api alembic upgrade head
	@echo "$(GREEN)✓ Migrations complete$(RESET)"

rollback: ## Rollback last migration
	$(COMPOSE) exec api alembic downgrade -1

migration: ## Create a new migration (usage: make migration name=add_users_table)
	$(COMPOSE) exec api alembic revision --autogenerate -m "$(name)"

db-shell: ## Open PostgreSQL shell
	$(COMPOSE) exec db psql -U $$(grep POSTGRES_USER .env | cut -d '=' -f2) -d $$(grep POSTGRES_DB .env | cut -d '=' -f2)

db-seed: ## Seed database with sample data
	$(COMPOSE) exec api python scripts/seed_data.py

# ── Testing ───────────────────────────────────────────────────
test: ## Run all tests
	@echo "$(CYAN)Running tests...$(RESET)"
	$(COMPOSE) exec api pytest tests/ -v --tb=short

test-api: ## Run API tests only
	$(COMPOSE) exec api pytest tests/test_api/ -v

test-models: ## Run ML model tests only
	$(COMPOSE) exec api pytest tests/test_models/ -v

test-cov: ## Run tests with coverage report
	$(COMPOSE) exec api pytest tests/ --cov=. --cov-report=html --cov-report=term-missing

lint: ## Lint and format code (ruff + black)
	ruff check services/api services/gee_pipeline services/ml_models --fix
	black services/api services/gee_pipeline services/ml_models

# ── GEE & GCP Auth ───────────────────────────────────────────
gee-auth: ## Authenticate with Google Earth Engine
	@echo "$(CYAN)Authenticating with Google Earth Engine...$(RESET)"
	earthengine authenticate
	@echo "$(GREEN)✓ GEE authenticated. Token saved.$(RESET)"

gcp-auth: ## Authenticate with Google Cloud Platform
	@echo "$(CYAN)Authenticating with GCP...$(RESET)"
	gcloud auth login
	gcloud config set project $(GCP_PROJECT)
	gcloud auth configure-docker
	@echo "$(GREEN)✓ GCP authenticated. Project: $(GCP_PROJECT)$(RESET)"

gcp-apis: ## Enable all required GCP APIs
	@echo "$(CYAN)Enabling GCP APIs...$(RESET)"
	gcloud services enable \
		run.googleapis.com \
		sql-component.googleapis.com \
		sqladmin.googleapis.com \
		artifactregistry.googleapis.com \
		secretmanager.googleapis.com \
		earthengine.googleapis.com \
		storage.googleapis.com \
		redis.googleapis.com \
		vpcaccess.googleapis.com
	@echo "$(GREEN)✓ APIs enabled$(RESET)"

# ── Build & Push ──────────────────────────────────────────────
build: ## Build Docker images
	docker build -t $(API_IMAGE):latest -f infrastructure/docker/api.Dockerfile services/api
	docker build -t $(DASHBOARD_IMAGE):latest -f infrastructure/docker/dashboard.Dockerfile services/dashboard

push: ## Push images to GCP Artifact Registry
	docker push $(API_IMAGE):latest
	docker push $(DASHBOARD_IMAGE):latest

# ── Infrastructure (Terraform) ────────────────────────────────
infra-init: ## Initialise Terraform
	cd infrastructure/terraform && terraform init

infra-plan: ## Show Terraform execution plan
	cd infrastructure/terraform && terraform plan -var="project_id=$(GCP_PROJECT)"

infra-apply: ## Apply Terraform infrastructure (creates GCP resources)
	@echo "$(YELLOW)This will create GCP resources and incur costs.$(RESET)"
	@read -p "Continue? [y/N] " confirm && [ "$$confirm" = "y" ]
	cd infrastructure/terraform && terraform apply -var="project_id=$(GCP_PROJECT)" -auto-approve

infra-destroy: ## Destroy all Terraform infrastructure (DANGER)
	@echo "$(YELLOW)DANGER: This will destroy all GCP resources!$(RESET)"
	@read -p "Type 'destroy' to confirm: " confirm && [ "$$confirm" = "destroy" ]
	cd infrastructure/terraform && terraform destroy -var="project_id=$(GCP_PROJECT)"

# ── Deployment ────────────────────────────────────────────────
deploy: build push ## Build, push, and deploy to Cloud Run
	@echo "$(CYAN)Deploying to GCP Cloud Run...$(RESET)"
	gcloud run deploy agrosense-api \
		--image $(API_IMAGE):latest \
		--region $(GCP_REGION) \
		--platform managed \
		--allow-unauthenticated
	gcloud run deploy agrosense-dashboard \
		--image $(DASHBOARD_IMAGE):latest \
		--region $(GCP_REGION) \
		--platform managed \
		--allow-unauthenticated
	@echo "$(GREEN)✓ Deployed to Cloud Run$(RESET)"

deploy-api: ## Deploy only the API
	gcloud run deploy agrosense-api \
		--image $(API_IMAGE):latest \
		--region $(GCP_REGION) \
		--platform managed

deploy-dashboard: ## Deploy only the dashboard
	gcloud run deploy agrosense-dashboard \
		--image $(DASHBOARD_IMAGE):latest \
		--region $(GCP_REGION) \
		--platform managed
