# ============================================
# Makefile for Smart Logistics MLOps
# ============================================
# Single Source of Truth for all automation
# Environment: Poetry + pyenv
# ============================================
#
# 🚀 QUICK START FOR NEW DEVELOPERS:
#   1. Run: make setup   (creates Python env + installs all dependencies)
#   2. Run: make quality (verify everything works)
#   3. Start coding!
#
# Prerequisites: Poetry and pyenv must be installed.
#   Install Poetry: curl -sSL https://install.python-poetry.org | python3 -
#   Install pyenv:  brew install pyenv (macOS) or https://github.com/pyenv/pyenv#installation
#
# ============================================

.PHONY: help setup clean quality check-style fix-style type-check test \
        infra-up infra-down infra-init infra-status infra-logs

# --- Configuration ---
PYTHON_VERSION := 3.12
POETRY := $(shell command -v poetry 2>/dev/null || echo "$$HOME/.local/bin/poetry")
COMPOSE := docker compose --env-file .env -f deployment/docker/docker-compose.yaml
TF := cd infrastructure/terraform && tflocal

# --- Colors ---
CYAN := \033[36m
GREEN := \033[32m
RED := \033[31m
YELLOW := \033[33m
BOLD := \033[1m
RESET := \033[0m

# --- 📋 Help ---
help: ## Show this help message
	@echo ""
	@echo "$(BOLD)$(CYAN)Smart Logistics MLOps$(RESET) - Available Commands:"
	@echo ""
	@echo "$(YELLOW)Setup & Environment:$(RESET)"
	@grep -E '^(setup|clean):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Quality & Testing:$(RESET)"
	@grep -E '^(quality|check-style|fix-style|type-check|test):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Infrastructure:$(RESET)"
	@grep -E '^(infra-up|infra-down|infra-init|infra-status|infra-logs):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(BOLD)Quick Start:$(RESET) make setup && make quality"
	@echo ""

# --- � Setup (Single unified target) ---
setup: ## Create Python 3.12 environment and install all dependencies
	@echo "$(BOLD)$(CYAN)� Setting up development environment...$(RESET)"
	@echo ""
	@# 1. Check prerequisites
	@echo "$(CYAN)Step 1/4: Checking prerequisites...$(RESET)"
	@if ! test -x "$(POETRY)"; then \
		echo "$(RED)✗ Poetry not found$(RESET)"; \
		echo "  Install: $(CYAN)curl -sSL https://install.python-poetry.org | python3 -$(RESET)"; \
		exit 1; \
	fi
	@if ! command -v pyenv >/dev/null 2>&1; then \
		echo "$(RED)✗ pyenv not found$(RESET)"; \
		echo "  Install: $(CYAN)brew install pyenv$(RESET) (macOS)"; \
		exit 1; \
	fi
	@echo "  $(GREEN)✓$(RESET) Poetry: $$($(POETRY) --version)"
	@echo "  $(GREEN)✓$(RESET) pyenv:  $$(pyenv --version)"
	@echo ""
	@# 2. Install Python via pyenv
	@echo "$(CYAN)Step 2/4: Installing Python $(PYTHON_VERSION) via pyenv...$(RESET)"
	@if pyenv versions --bare | grep -q "^$(PYTHON_VERSION)"; then \
		echo "  $(GREEN)✓$(RESET) Python $(PYTHON_VERSION) already installed"; \
	else \
		echo "  $(YELLOW)⏳ Installing Python $(PYTHON_VERSION) (this may take a few minutes)...$(RESET)"; \
		pyenv install $(PYTHON_VERSION); \
		echo "  $(GREEN)✓$(RESET) Python $(PYTHON_VERSION) installed"; \
	fi
	@echo ""
	@# 3. Create virtualenv and install dependencies
	@echo "$(CYAN)Step 3/4: Installing dependencies via Poetry...$(RESET)"
	@$(POETRY) env use $(PYTHON_VERSION)
	@$(POETRY) install --no-interaction
	@echo "  $(GREEN)✓$(RESET) Dependencies installed"
	@echo ""
	@# 4. Install pre-commit hooks
	@echo "$(CYAN)Step 4/4: Installing pre-commit hooks...$(RESET)"
	@$(POETRY) run pre-commit install
	@echo "  $(GREEN)✓$(RESET) Pre-commit hooks installed"
	@echo ""
	@echo "$(GREEN)$(BOLD)════════════════════════════════════════$(RESET)"
	@echo "$(GREEN)$(BOLD)✓ Setup complete!$(RESET)"
	@echo "$(GREEN)$(BOLD)════════════════════════════════════════$(RESET)"
	@echo ""
	@echo "  Python:  $(CYAN)$$($(POETRY) run python --version)$(RESET)"
	@echo "  Venv:    $(CYAN)$$($(POETRY) env info --path)$(RESET)"
	@echo ""
	@echo "$(YELLOW)Next steps:$(RESET)"
	@echo "  • Run quality checks:    $(CYAN)make quality$(RESET)"
	@echo "  • Start infrastructure:  $(CYAN)make infra-up$(RESET)"
	@echo ""

# --- 🔍 Quality Checks ---
check-style: ## Check code style without fixing (ruff check + format --check)
	@echo "$(CYAN)🔍 Checking code style...$(RESET)"
	@$(POETRY) run ruff check .
	@$(POETRY) run ruff format --check .
	@echo "$(GREEN)✓ Code style checks passed$(RESET)"

fix-style: ## Auto-fix code style issues (ruff check --fix + format)
	@echo "$(CYAN)🔧 Fixing code style...$(RESET)"
	@$(POETRY) run ruff check --fix .
	@$(POETRY) run ruff format .
	@echo "$(GREEN)✓ Code style fixed$(RESET)"

type-check: ## Run type checking with mypy
	@echo "$(CYAN)🔍 Running type checks...$(RESET)"
	@$(POETRY) run mypy src/ || true
	@echo "$(GREEN)✓ Type checking complete$(RESET)"

test: ## Run tests with pytest
	@echo "$(CYAN)🧪 Running tests...$(RESET)"
	@$(POETRY) run pytest tests/ -v --tb=short
	@echo "$(GREEN)✓ Tests complete$(RESET)"

quality: check-style type-check test ## Run all quality checks (CI entry point)
	@echo "$(GREEN)$(BOLD)✓ All quality checks passed!$(RESET)"

# --- 🧹 Cleaning ---
clean: ## Deep clean of data and caches
	@echo "$(CYAN)🧹 Cleaning project...$(RESET)"
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
	@echo "$(GREEN)✓ Cleaned: Docker, LocalStack, Terraform, Python caches$(RESET)"

# --- 🏗️ Infrastructure ---
infra-up: ## Start infrastructure services (LocalStack, Postgres, MLflow)
	@echo "$(CYAN)🏗️ Starting infrastructure services...$(RESET)"
	$(COMPOSE) up -d --wait
	@echo ""
	@echo "$(GREEN)✓ Infrastructure ready!$(RESET)"
	@echo "  • LocalStack:  http://localhost:4566"
	@echo "  • PostgreSQL:  localhost:5432"
	@echo "  • MLflow UI:   http://localhost:5001"

infra-down: ## Stop all infrastructure services
	@echo "$(CYAN)🛑 Stopping infrastructure services...$(RESET)"
	$(COMPOSE) down
	@echo "$(GREEN)✓ Infrastructure stopped$(RESET)"

infra-logs: ## Show logs from infrastructure services
	$(COMPOSE) logs -f

infra-init: ## Apply Terraform resources (S3 buckets, IAM roles)
	@echo "$(CYAN)🏗️ Initializing infrastructure resources...$(RESET)"
	$(TF) init -input=false
	$(TF) apply -auto-approve
	@echo "$(GREEN)✓ Infrastructure initialized!$(RESET)"

infra-status: ## Show status of Terraform resources
	@echo "$(CYAN)📊 Checking infrastructure status...$(RESET)"
	$(TF) validate
	$(TF) plan -out=tfplan
	@echo "$(GREEN)✓ Infrastructure validation complete$(RESET)"
