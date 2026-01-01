# ============================================
# Makefile for Smart Logistics MLOps
# ============================================
# Bare-metal development: Python runs locally, Docker for infrastructure only
# ============================================

.PHONY: help setup clean quality infra-up infra-down infra-init

# --- Configuration ---
COMPOSE := docker compose --env-file .env -f deployment/docker/docker-compose.yaml
TF := cd infrastructure/terraform && tflocal

# --- 📋 Help ---
help: ## Show this help message
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "\033[36m%-15s\033[0m %s\n", $$1, $$2}'

# --- 🚀 Setup & Quality ---
setup: ## Full setup: install deps and hooks
	poetry install
	pre-commit install
	$(TF) init

clean: ## Deep clean of data and caches
	$(COMPOSE) down -v 2>/dev/null || true
	rm -rf deployment/docker/.localstack
	rm -rf infrastructure/terraform/.terraform
	rm -f infrastructure/terraform/terraform.tfstate*
	rm -f infrastructure/terraform/tfplan
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ dist/ build/ *.egg-info/
	@echo "✓ Cleaned: Docker, LocalStack, Terraform, Python caches"

quality: ## Run lint, type-check, and tests
	ruff check .
	ruff format --check .
	mypy src/ || true
	pytest tests/ -v --tb=short

format: ## Auto-format code with ruff
	ruff check --fix .
	ruff format .

# --- 🏗️ Infrastructure ---
infra-up: ## Start infrastructure services (LocalStack, Postgres, MLflow)
	$(COMPOSE) up -d --wait
	@echo ""
	@echo "✓ Infrastructure ready!"
	@echo "  • LocalStack:  http://localhost:4566"
	@echo "  • PostgreSQL:  localhost:5432"
	@echo "  • MLflow UI:   http://localhost:5001"

infra-down: ## Stop all infrastructure services
	$(COMPOSE) down

infra-logs: ## Show logs from infrastructure services
	$(COMPOSE) logs -f

infra-init: ## Apply Terraform resources (S3 buckets, IAM roles)
	$(TF) apply -auto-approve
	@echo "✓ Infrastructure initialized!"
	@awslocal s3 ls 2>/dev/null || echo "Run 'awslocal s3 ls' to verify buckets"
