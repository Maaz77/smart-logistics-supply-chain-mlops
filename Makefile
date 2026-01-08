# ============================================
# Makefile for Smart Logistics MLOps
# ============================================
# Single Source of Truth for all automation
# Environment: Poetry + pyenv
# ============================================
#
# 🚀 QUICK START FOR NEW DEVELOPERS:
#   1. Run: make setup   (creates Python env + installs all dependencies)
#   2. Start coding!
#
# Prerequisites: Poetry and pyenv must be installed.
#   Install Poetry: curl -sSL https://install.python-poetry.org | python3 -
#   Install pyenv:  brew install pyenv (macOS) or https://github.com/pyenv/pyenv#installation
#
# ============================================

.PHONY: help setup clean fix-style type-check test test-serving \
        infra-up infra-down ml-services-up ml-services-down s3-sync reset-infra \
        pipeline grafana-up grafana-down monitoring \
        setup-k8s down-k8s argocd-password

# --- Configuration ---
PYTHON_VERSION := 3.12
POETRY := $(shell command -v poetry 2>/dev/null || echo "$$HOME/.local/bin/poetry")
COMPOSE_AWS := docker compose -f infra_aws/docker/docker-compose.yaml
COMPOSE_MLOPS := docker compose -f mlops_services/docker/docker-compose.yaml
COMPOSE_AIRFLOW := docker compose -f mlops_services/docker/docker-compose.airflow.yaml
COMPOSE_MONITORING := docker compose -f mlops_services/docker/docker-compose.yaml -f monitoring/docker/docker-compose.monitoring.yaml
COMPOSE_SERVING := docker compose -f serving/docker/docker-compose.serving.yaml
TF := cd infra_aws/terraform && $(POETRY) run tflocal
# LocalStack AWS CLI - uses awslocal via Poetry
AWS_LOCAL := $(POETRY) run awslocal

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
	@grep -E '^(fix-style|type-check|test|test-serving):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Infrastructure:$(RESET)"
	@grep -E '^(infra-up|infra-down|s3-sync|reset-infra):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)ML Services:$(RESET)"
	@grep -E '^(ml-services-up|ml-services-down):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Monitoring:$(RESET)"
	@grep -E '^(grafana-up|grafana-down|monitoring):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo "$(YELLOW)Run ML Pipeline on your bare local machine:$(RESET)"
	@grep -E '^(pipeline):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
	@echo ""
	@echo ""
	@echo "$(YELLOW)Model Serving Deployed on Kubernetes:$(RESET)"
	@grep -E '^(setup-k8s|down-k8s|argocd-password):.*?## .*$$' $(MAKEFILE_LIST) | awk 'BEGIN {FS = ":.*?## "}; {printf "  $(CYAN)%-18s$(RESET) %s\n", $$1, $$2}'
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
	@echo "  • Start infrastructure:  $(CYAN)make infra-up$(RESET)"
	@echo ""

# --- 🔍 Quality Checks ---
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

test-serving: ## Run integration tests for serving (API + UI)
	@echo "$(CYAN)🧪 Running serving integration tests...$(RESET)"
	@export PYTHONPATH=$$PYTHONPATH:. && \
	$(POETRY) run pytest tests/test_api.py tests/test_ui.py -v --tb=short
	@echo "$(GREEN)✓ Serving integration tests complete$(RESET)"


# --- 🧹 Cleaning ---
# --- 🧹 Cleaning ---
clean: ## Clean Python caches (preserves all infrastructure state)
	@echo "$(CYAN)🧹 Cleaning Python caches...$(RESET)"
	$(COMPOSE_MLOPS) down 2>/dev/null || true
	$(COMPOSE_AWS) down 2>/dev/null || true
	find . -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".pytest_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".mypy_cache" -exec rm -rf {} + 2>/dev/null || true
	find . -type d -name ".ruff_cache" -exec rm -rf {} + 2>/dev/null || true
	rm -rf .coverage htmlcov/ dist/ build/ *.egg-info/
	@echo "$(GREEN)✓ Cleaned: Python caches$(RESET)"
	@echo "$(YELLOW)ℹ Preserved: Infrastructure state (Terraform, LocalStack, DB, S3)$(RESET)"

reset-infra: ## ⚠️  Wipe all infrastructure state (Terraform, LocalStack)
	@echo "$(RED)⚠️  Resetting infrastructure state...$(RESET)"
	@echo "$(RED)This will delete LocalStack data and Terraform state.$(RESET)"
	@echo "$(CYAN)  Stopping containers and removing volumes...$(RESET)"
	$(COMPOSE_AWS) down -v 2>/dev/null || true
	$(COMPOSE_MLOPS) down -v 2>/dev/null || true
	@echo "$(CYAN)  Removing LocalStack named volume...$(RESET)"
	docker volume rm infra_aws_docker_localstack_data 2>/dev/null || true
	@echo "$(CYAN)  Removing old LocalStack bind mount directory (if exists)...$(RESET)"
	rm -rf infra_aws/.localstack
	@echo "$(CYAN)  Removing Terraform state and working files...$(RESET)"
	rm -rf infra_aws/terraform/.terraform
	rm -f infra_aws/terraform/terraform.tfstate*
	rm -f infra_aws/terraform/tfplan
	rm -f infra_aws/terraform/.terraform.lock.hcl
	@echo "$(GREEN)✓ Reset: Infrastructure state cleared$(RESET)"
	@echo "$(YELLOW)ℹ Note: Persistent folders (data/, models/, mlops_services/postgres_data/) were NOT deleted.$(RESET)"

# --- 🏗️ Infrastructure ---
infra-up: ## Start AWS infrastructure (LocalStack, Terraform, S3 sync)
	@echo "$(CYAN)🏗️ Starting AWS infrastructure...$(RESET)"
	@echo "$(CYAN)  Creating persistent folders if needed...$(RESET)"
	@mkdir -p data models
	@echo "$(CYAN)  Starting LocalStack...$(RESET)"
	@$(COMPOSE_AWS) up -d --wait
	@echo ""
	@echo "$(BOLD)$(CYAN)🔧 Applying Terraform resources...$(RESET)"
	@echo "$(CYAN)  Using tflocal for LocalStack...$(RESET)"
	@$(TF) init -input=false
	@$(TF) apply -auto-approve
	@echo "$(GREEN)✓ Infrastructure initialized!$(RESET)"
	@echo ""
	@echo "$(YELLOW)S3 Buckets created (LocalStack):$(RESET)"
	@$(AWS_LOCAL) s3 ls 2>/dev/null || true
	@echo ""
	@echo "$(BOLD)$(CYAN)🔄 Syncing S3 buckets with local folders...$(RESET)"
	@$(POETRY) run python infra_aws/scripts/s3_sync.py || true
	@echo "$(GREEN)✓ S3 sync complete!$(RESET)"
	@echo ""
	@echo "$(GREEN)✓ AWS infrastructure ready!$(RESET)"
	@echo "  • LocalStack:  http://localhost:4566"
	@echo ""
	@echo "$(YELLOW)S3 Buckets (synced with local folders):$(RESET)"
	@echo "  • s3://smart-logistics-data   ↔ ./data"
	@echo "  • s3://mlflow-model-registry  ↔ ./models"

ml-services-up: ## Start MLOps services (Postgres, MLflow, Airflow)
	@echo "$(CYAN)🏗️ Starting MLOps services...$(RESET)"
	@echo "$(CYAN)  Creating persistent folders if needed...$(RESET)"
	@mkdir -p mlops_services/postgres_data
	@echo "$(CYAN)  Starting MLOps services (Postgres, MLflow)...$(RESET)"
	@$(COMPOSE_MLOPS) up -d --wait
	@echo ""
	@echo "$(BOLD)$(CYAN)🌀 Starting Airflow...$(RESET)"
	@echo "$(CYAN)  Building Airflow images...$(RESET)"
	@$(COMPOSE_MLOPS) -f mlops_services/docker/docker-compose.airflow.yaml build
	@echo "$(CYAN)  Starting Airflow services...$(RESET)"
	@$(COMPOSE_MLOPS) -f mlops_services/docker/docker-compose.airflow.yaml up -d --wait
	@echo ""
	@echo "$(GREEN)✓ MLOps services ready!$(RESET)"
	@echo "  • PostgreSQL:  localhost:5432"
	@echo "  • MLflow UI:   http://localhost:5001"
	@echo "  • Airflow UI:  http://localhost:8080 (Login: admin/admin)"
	@echo "  • Adminer:     http://localhost:8081"
	@echo ""
	@echo "$(YELLOW)Persistent storage:$(RESET)"
	@echo "  • PostgreSQL data (mlflow, airflow, monitoring, serving) → ./mlops_services/postgres_data"

infra-down: ## Stop AWS infrastructure (syncs S3 to local first)
	@echo "$(CYAN)🔄 Syncing S3 buckets to local folders...$(RESET)"
	@$(POETRY) run python infra_aws/scripts/s3_sync.py || true
	@echo "$(CYAN)🛑 Stopping AWS infrastructure...$(RESET)"
	@$(COMPOSE_AWS) down
	@echo "$(GREEN)✓ AWS infrastructure stopped$(RESET)"
	@echo "$(YELLOW)ℹ Persistent data preserved in: data/, models/$(RESET)"

ml-services-down: ## Stop MLOps services (Postgres, MLflow, Airflow)
	@echo "$(CYAN)🛑 Stopping Airflow...$(RESET)"
	@$(COMPOSE_MLOPS) -f mlops_services/docker/docker-compose.airflow.yaml down
	@echo "$(CYAN)🛑 Stopping MLOps services...$(RESET)"
	@$(COMPOSE_MLOPS) down
	@echo "$(GREEN)✓ MLOps services stopped$(RESET)"
	@echo "$(YELLOW)ℹ Persistent data preserved in: mlops_services/postgres_data/$(RESET)"

s3-sync: ## Sync S3 buckets with local folders (bidirectional via LocalStack)
	@$(POETRY) run python infra_aws/scripts/s3_sync.py

# --- 📊 Monitoring ---
grafana-up: ## Start Grafana service container
	@echo "$(CYAN)📊 Starting Grafana services...$(RESET)"
	@echo "$(YELLOW)  Prerequisites:$(RESET)"
	@echo "    • Infrastructure must be running: $(CYAN)make infra-up$(RESET)"
	@echo "    • MLOps services must be running: $(CYAN)make ml-services-up$(RESET)"
	@echo "    • Note: Monitoring database is created automatically by PostgreSQL init script"
	@echo ""
	@echo "$(CYAN)  Starting Grafana...$(RESET)"
	@$(COMPOSE_MONITORING) up -d --wait grafana
	@echo ""
	@echo "$(GREEN)✓ Grafana services ready!$(RESET)"
	@echo "  • Grafana:  http://localhost:3000 (Login: admin/admin)"

grafana-down: ## Stop Grafana services - does not affect MLflow/PostgreSQL
	@echo "$(CYAN)🛑 Stopping Grafana services...$(RESET)"
	@$(COMPOSE_MONITORING) stop grafana
	@$(COMPOSE_MONITORING) rm -f grafana
	@echo "$(GREEN)✓ Grafana services stopped (MLOps services still running)$(RESET)"

monitoring: ## Run model monitoring simulation (calculates some Evidently metrics day-by-day and logs to monitoring database)
	@echo "$(BOLD)$(CYAN)📊 Running Model Monitoring Simulation$(RESET)"
	@echo ""
	@echo "$(YELLOW)Prerequisites:$(RESET)"
	@echo "  • Infrastructure must be running: $(CYAN)make infra-up$(RESET)"
	@echo "  • Monitoring database initialized: $(CYAN)make grafana-up$(RESET)"
	@echo ""
	@echo "$(CYAN)Starting monitoring simulation...$(RESET)"
	@echo "$(YELLOW)This will process validation data day-by-day with 20-second pauses$(RESET)"
	@echo ""
	@$(POETRY) run python -m src.monitoring
	@echo ""
	@echo "$(GREEN)$(BOLD)════════════════════════════════════════$(RESET)"
	@echo "$(GREEN)$(BOLD)✓ Monitoring simulation complete!$(RESET)"
	@echo "$(GREEN)$(BOLD)════════════════════════════════════════$(RESET)"
	@echo ""
	@echo "$(YELLOW)View results:$(RESET)"
	@echo "  • Grafana:  $(CYAN)http://localhost:3000$(RESET) (Login: admin/admin)"
	@echo "  • Adminer:  $(CYAN)http://localhost:8081$(RESET)"
	@echo ""

# ---  ML Pipeline ---
pipeline: ## Run the ML Pipeline on your bare local machine using MLFlow service and AWS S3 buckets for data and model storage
	@echo "$(BOLD)$(CYAN)🚀 Running ML Pipeline$(RESET)"
	@echo ""
	@echo "$(CYAN)Step 1/3: Data Ingestion$(RESET)"
	@$(POETRY) run python -m src.ml_pipeline.ingest
	@echo ""
	@echo "$(CYAN)Step 2/3: Feature Engineering$(RESET)"
	@$(POETRY) run python -m src.ml_pipeline.preprocess
	@echo ""
	@echo "$(CYAN)Step 3/3: Model Training$(RESET)"
	@$(POETRY) run python -m src.ml_pipeline.train
	@echo ""
	@echo "$(GREEN)$(BOLD)════════════════════════════════════════$(RESET)"
	@echo "$(GREEN)$(BOLD)✓ Pipeline complete!$(RESET)"
	@echo "$(GREEN)$(BOLD)════════════════════════════════════════$(RESET)"
	@echo ""
	@echo "$(YELLOW)View results:$(RESET)"
	@echo "  • MLflow UI:   $(CYAN)http://localhost:5001$(RESET)"
	@echo "  • S3 data:     $(CYAN)poetry run awslocal s3 ls s3://smart-logistics-data/ --recursive$(RESET)"
	@echo ""

# --- ☸️  Kubernetes ---
setup-k8s: ## Setup Kubernetes cluster (Kind) and install ArgoCD
	@echo "$(BOLD)$(CYAN)☸️  Setting up Kubernetes Infrastructure$(RESET)"
	@echo ""
	@if [ ! -f "k8s/setup_k8s.sh" ]; then \
		echo "$(RED)✗ Setup script not found: k8s/setup_k8s.sh$(RESET)"; \
		exit 1; \
	fi
	@sh k8s/setup_k8s.sh
	@echo ""
	@echo "$(GREEN)✓ Kubernetes setup complete!$(RESET)"
	@echo ""
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo "$(BOLD)$(CYAN)📡 Access Hints$(RESET)"
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"
	@echo ""
	@echo "$(CYAN)ArgoCD UI:$(RESET)"
	@PASSWORD=$$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d 2>/dev/null 2>/dev/null || echo ""); \
	if [ -n "$$PASSWORD" ]; then \
		echo "  Password: $(BOLD)$$PASSWORD$(RESET) (username: $(BOLD)admin$(RESET))"; \
	else \
		echo "  Password: $(YELLOW)Run 'make argocd-password' to get it$(RESET)"; \
	fi; \
	echo "  Port forward: $(BOLD)kubectl port-forward svc/argocd-server -n argocd 8088:443$(RESET)"; \
	echo "  URL: $(BOLD)https://localhost:8088$(RESET)"
	@echo ""
	@echo "$(CYAN)Application UI:$(RESET)"
	@echo "  Port forward: $(BOLD)kubectl port-forward svc/serving-ui-service -n mlops-production 8501:8501$(RESET)"
	@echo "  URL: $(BOLD)http://localhost:8501$(RESET)"
	@echo ""
	@echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"


down-k8s: ## Shut down Kind Kubernetes cluster (deletes cluster and all resources including ArgoCD)
	@echo "$(BOLD)$(CYAN)🛑 Shutting down Kind Kubernetes cluster$(RESET)"
	@echo ""
	@CLUSTER_NAME="modelserving-cluster"; \
	if command -v kind >/dev/null 2>&1 && kind get clusters 2>/dev/null | grep -q "^$$CLUSTER_NAME$$"; then \
		echo "$(CYAN)Deleting Kind cluster '$$CLUSTER_NAME'...$(RESET)"; \
		kind delete cluster --name "$$CLUSTER_NAME" 2>/dev/null || true; \
		echo "$(GREEN)✓ Kind cluster deleted (all resources including ArgoCD removed)$(RESET)"; \
	else \
		echo "$(YELLOW)⚠ Cluster '$$CLUSTER_NAME' not found or kind not installed$(RESET)"; \
	fi
	@echo ""
	@echo "$(GREEN)✓ Kubernetes shutdown complete!$(RESET)"

argocd-password: ## Print ArgoCD UI admin password
	@echo "$(BOLD)$(CYAN)🔐 ArgoCD Admin Password$(RESET)"
	@echo ""
	@if ! kubectl cluster-info &> /dev/null; then \
		echo "$(RED)✗ Kubernetes cluster not accessible$(RESET)"; \
		echo "  Run: $(CYAN)make setup-k8s$(RESET) first"; \
		exit 1; \
	fi
	@if ! kubectl get namespace argocd &> /dev/null; then \
		echo "$(RED)✗ ArgoCD namespace not found$(RESET)"; \
		echo "  Run: $(CYAN)make setup-k8s$(RESET) to install ArgoCD"; \
		exit 1; \
	fi
	@PASSWORD=$$(kubectl -n argocd get secret argocd-initial-admin-secret -o jsonpath="{.data.password}" 2>/dev/null | base64 -d 2>/dev/null); \
	if [ -z "$$PASSWORD" ]; then \
		echo "$(YELLOW)⚠ ArgoCD admin secret not found or not ready yet$(RESET)"; \
		echo "  Wait a few moments and try again, or check ArgoCD pods:"; \
		echo "  $(CYAN)kubectl get pods -n argocd$(RESET)"; \
		exit 1; \
	fi; \
	echo "$(GREEN)Username:$(RESET) $(BOLD)admin$(RESET)"; \
	echo "$(GREEN)Password:$(RESET) $(BOLD)$$PASSWORD$(RESET)"; \
	echo ""; \
	echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"; \
	echo "$(BOLD)$(CYAN)📡 How to Access ArgoCD UI:$(RESET)"; \
	echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"; \
	echo ""; \
	echo "  $(CYAN)Step 1:$(RESET) Start port forwarding (run in a separate terminal):"; \
	echo "    $(BOLD)kubectl port-forward svc/argocd-server -n argocd 8088:443$(RESET)"; \
	echo ""; \
	echo "  $(CYAN)Step 2:$(RESET) Open your browser and navigate to:"; \
	echo "    $(BOLD)https://localhost:8088$(RESET)"; \
	echo ""; \
	echo "  $(CYAN)Step 3:$(RESET) Accept the SSL certificate warning (self-signed cert)"; \
	echo ""; \
	echo "  $(CYAN)Step 4:$(RESET) Login with the credentials shown above"; \
	echo ""; \
	echo "$(YELLOW)━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━$(RESET)"; \
	echo ""; \
	echo "$(YELLOW)ℹ Note:$(RESET) ArgoCD automatically syncs deployments from git. No manual deployment needed!"
