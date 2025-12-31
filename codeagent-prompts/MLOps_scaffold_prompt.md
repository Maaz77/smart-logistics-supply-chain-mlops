# MLOps Project Scaffolding + Tooling Bootstrap – Coding Agent Instructions

## Role and Context

You are a **coding agent acting as a senior MLOps engineer**.

A **bare Conda environment already exists** on the system:

```
Conda environment name: MLOpspy312
Python version: 3.12
```

This environment currently contains **only Python**, with **no MLOps tooling installed**.

Your task is to:

1. **Use the existing Conda environment (`MLOpspy312`)**
2. **Install all foundational MLOps tools required at this stage**
3. **Scaffold a production-grade MLOps project structure**
4. **Generate configuration and placeholder files**
5. **Prepare the repository for future full pipeline development**

---

## Critical Constraints (Must Follow)

### ✅ You MUST
- Use the existing Conda environment: `MLOpspy312`
- Install foundational tooling (Poetry, DVC, MLflow, Airflow CLI, etc.)
- Create filesystem structure and configuration files
- Keep everything cloud- and Kubernetes-compatible

### ❌ You MUST NOT
- Download any datasets
- Train any ML models
- Install heavy ML libraries (e.g. torch, tensorflow, xgboost, sklearn)
- Write business logic or feature engineering code
- Hardcode secrets or credentials

---

## Step 1 — Environment Usage

Use the existing Conda environment explicitly.
Do **not** create a new Conda environment.

---

## Step 2 — Tooling to Install

Install the following tools **inside `MLOpspy312`**:

- Poetry
- DVC
- MLflow
- Apache Airflow (local setup)
- pytest
- pre-commit
- black or ruff
- docker-compose (if available)

These are **tooling dependencies**, not ML libraries.

---

## Step 3 — Project Structure

Create a professional MLOps monorepo compatible with:

- Poetry
- DVC
- MLflow
- Airflow
- GitHub Actions
- Docker
- Kubernetes
- GitOps

(Structure detailed in the original prompt.)

---

## Step 4 — Configuration & Documentation

Generate:
- `pyproject.toml`
- `poetry.lock`
- DVC configuration
- Airflow DAG skeleton
- GitHub Actions CI/CD YAMLs
- Kubernetes placeholders
- README.md with setup instructions

---

## Final Reminder

This step is **bootstrap + scaffolding only**.
No data, no models, no training.
