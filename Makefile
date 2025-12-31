# Makefile for Smart Logistics Supply Chain ML
# Production-grade MLOps automation commands

.PHONY: help setup infra-up infra-init infra-down infra-destroy test lint format clean all

# Default target
.DEFAULT_GOAL := help

# Colors for terminal output
CYAN := \033[36m
GREEN := \033[32m
YELLOW := \033[33m
RED := \033[31m
RESET := \033[0m

# Configuration
DOCKER_COMPOSE_BASE := deployment/docker/docker-compose.yaml
DOCKER_COMPOSE_DEV := deployment/docker/docker-compose.dev.yaml
TERRAFORM_DIR := infrastructure/terraform
LOCALSTACK_DIR := deployment/docker/.localstack

##@ Help
help: ## Display this help message
	@awk 'BEGIN {FS = ":.*##"; printf "\n$(CYAN)Usage:$(RESET)\n  make $(GREEN)<target>$(RESET)\n"} /^[a-zA-Z_0-9-]+:.*?##/ { printf "  $(GREEN)%-15s$(RESET) %s\n", $$1, $$2 } /^##@/ { printf "\n$(CYAN)%s$(RESET)\n", substr($$0, 5) } ' $(MAKEFILE_LIST)

##@ Setup
setup: ## Install poetry, pre-commit hooks, and initialize terraform
	@echo "$(CYAN)Installing Poetry...$(RESET)"
	@command -v poetry >/dev/null 2>&1 || curl -sSL https://install.python-poetry.org | python3 -
	@echo "$(CYAN)Installing Python dependencies...$(RESET)"
	@poetry install --no-interaction
	@echo "$(CYAN)Installing pre-commit hooks...$(RESET)"
	@poetry run pre-commit install
	@echo "$(CYAN)Initializing Terraform (tflocal for LocalStack)...$(RESET)"
	@cd $(TERRAFORM_DIR) && tflocal init
	@echo "$(GREEN)✓ Setup complete!$(RESET)"

install: ## Install Python dependencies only
	@echo "$(CYAN)Installing Python dependencies...$(RESET)"
	@poetry install --no-interaction
	@echo "$(GREEN)✓ Dependencies installed!$(RESET)"

##@ Infrastructure
infra-up: ## Start all infrastructure services (LocalStack, Postgres, MLflow)
	@echo "$(CYAN)Creating LocalStack data directory...$(RESET)"
	@mkdir -p $(LOCALSTACK_DIR)
	@echo "$(CYAN)Starting base infrastructure (LocalStack)...$(RESET)"
	@docker-compose -f $(DOCKER_COMPOSE_BASE) up -d
	@echo "$(CYAN)Waiting for LocalStack to be healthy...$(RESET)"
	@timeout 60 bash -c 'until docker exec localstack curl -s http://localhost:4566/_localstack/health | grep -q "running\|available"; do echo "Waiting..."; sleep 2; done' || echo "$(YELLOW)Warning: LocalStack health check timed out$(RESET)"
	@echo "$(CYAN)Starting development services (Postgres, MLflow)...$(RESET)"
	@docker-compose -f $(DOCKER_COMPOSE_BASE) -f $(DOCKER_COMPOSE_DEV) up -d
	@echo "$(CYAN)Waiting for services to be healthy...$(RESET)"
	@sleep 10
	@echo "$(GREEN)✓ Infrastructure is up!$(RESET)"
	@echo ""
	@echo "$(CYAN)Service URLs:$(RESET)"
	@echo "  MLflow UI:    http://localhost:5000"
	@echo "  LocalStack:   http://localhost:4566"
	@echo "  Postgres:     localhost:5432"

infra-init: ## Initialize infrastructure in LocalStack (create S3 buckets, IAM roles)
	@echo "$(CYAN)Running tflocal apply against LocalStack...$(RESET)"
	@cd $(TERRAFORM_DIR) && tflocal apply -auto-approve
	@echo "$(GREEN)✓ Infrastructure initialized!$(RESET)"
	@echo ""
	@echo "$(CYAN)Verifying S3 buckets...$(RESET)"
	@awslocal s3 ls || aws --endpoint-url=http://localhost:4566 s3 ls || echo "$(YELLOW)Note: Install AWS CLI or awslocal to verify buckets$(RESET)"

infra-plan: ## Show Terraform plan
	@echo "$(CYAN)Running tflocal plan...$(RESET)"
	@cd $(TERRAFORM_DIR) && tflocal plan

infra-destroy: ## Destroy infrastructure in LocalStack
	@echo "$(CYAN)Running tflocal destroy against LocalStack...$(RESET)"
	@cd $(TERRAFORM_DIR) && tflocal destroy -auto-approve
	@echo "$(GREEN)✓ Infrastructure destroyed!$(RESET)"

infra-down: ## Stop all infrastructure services
	@echo "$(CYAN)Stopping all services...$(RESET)"
	@docker-compose -f $(DOCKER_COMPOSE_BASE) -f $(DOCKER_COMPOSE_DEV) down
	@echo "$(GREEN)✓ Infrastructure stopped!$(RESET)"

infra-logs: ## Show logs from all services
	@docker-compose -f $(DOCKER_COMPOSE_BASE) -f $(DOCKER_COMPOSE_DEV) logs -f

infra-status: ## Show status of all services
	@echo "$(CYAN)Docker containers:$(RESET)"
	@docker-compose -f $(DOCKER_COMPOSE_BASE) -f $(DOCKER_COMPOSE_DEV) ps
	@echo ""
	@echo "$(CYAN)LocalStack health:$(RESET)"
	@curl -s http://localhost:4566/_localstack/health | python3 -m json.tool 2>/dev/null || echo "LocalStack not running"

##@ Quality
test: ## Run pytest test suite
	@echo "$(CYAN)Running tests...$(RESET)"
	@poetry run pytest tests/ -v --tb=short
	@echo "$(GREEN)✓ Tests complete!$(RESET)"

test-cov: ## Run tests with coverage report
	@echo "$(CYAN)Running tests with coverage...$(RESET)"
	@poetry run pytest tests/ -v --cov=src --cov-report=html --cov-report=term
	@echo "$(GREEN)✓ Coverage report generated in htmlcov/$(RESET)"

lint: ## Run all linters (ruff, mypy)
	@echo "$(CYAN)Running Ruff linter...$(RESET)"
	@poetry run ruff check .
	@echo "$(CYAN)Running Ruff formatter check...$(RESET)"
	@poetry run ruff format --check .
	@echo "$(CYAN)Running MyPy type checker...$(RESET)"
	@poetry run mypy src/ || true
	@echo "$(GREEN)✓ Linting complete!$(RESET)"

format: ## Auto-format code with ruff
	@echo "$(CYAN)Formatting code with Ruff...$(RESET)"
	@poetry run ruff check --fix .
	@poetry run ruff format .
	@echo "$(GREEN)✓ Formatting complete!$(RESET)"

pre-commit: ## Run pre-commit hooks on all files
	@echo "$(CYAN)Running pre-commit hooks...$(RESET)"
	@poetry run pre-commit run --all-files

##@ Cleanup
clean: ## Stop containers and wipe LocalStack data
	@echo "$(CYAN)Stopping all containers...$(RESET)"
	@docker-compose -f $(DOCKER_COMPOSE_BASE) -f $(DOCKER_COMPOSE_DEV) down -v --remove-orphans 2>/dev/null || true
	@echo "$(CYAN)Removing LocalStack data...$(RESET)"
	@rm -rf $(LOCALSTACK_DIR)
	@echo "$(CYAN)Removing Python cache...$(RESET)"
	@find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete 2>/dev/null || true
	@echo "$(GREEN)✓ Cleanup complete!$(RESET)"

clean-docker: ## Remove all Docker resources (containers, images, volumes)
	@echo "$(RED)Warning: This will remove all project Docker resources!$(RESET)"
	@docker-compose -f $(DOCKER_COMPOSE_BASE) -f $(DOCKER_COMPOSE_DEV) down -v --rmi local --remove-orphans 2>/dev/null || true
	@echo "$(GREEN)✓ Docker cleanup complete!$(RESET)"

##@ Development Workflow
all: setup infra-up infra-init ## Complete setup: install deps, start infra, init terraform
	@echo "$(GREEN)✓ Full setup complete!$(RESET)"
	@echo ""
	@echo "$(CYAN)Next steps:$(RESET)"
	@echo "  1. Open MLflow UI at http://localhost:5000"
	@echo "  2. Run 'make test' to verify tests pass"
	@echo "  3. Run 'make lint' to check code quality"

dev: infra-up ## Start development environment
	@echo "$(GREEN)✓ Development environment ready!$(RESET)"

restart: infra-down infra-up ## Restart all infrastructure
	@echo "$(GREEN)✓ Infrastructure restarted!$(RESET)"
