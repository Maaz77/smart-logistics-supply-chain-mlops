### CODING_AGENT_PROMPT: Makefile Hardening & CI/CD Integration

**Context:** You are refining the automation layer for "smart-logistics-mlops". The goal is to make the Makefile the primary interface for both humans and CI machines, grouping commands logically to avoid a "messy" root.

**Task:**
Refactor the root `Makefile` and update the GitHub Actions/Pre-commit configurations to use these grouped targets.

**1. Refactor `Makefile` into Groups:**
Use comments to visually group targets and implement a `help` target.
- **Group: Setup**
  - `setup`: Install dependencies (poetry), pre-commit hooks, and init terraform.
  - `clean`: Remove python caches, build artifacts, and localstack data.
- **Group: Quality (The "CI" targets)**
  - `lint`: Run ruff check and format.
  - `type-check`: Run mypy.
  - `test`: Run pytest with coverage.
  - `quality`: One target that runs `lint`, `type-check`, and `test`.
- **Group: Infrastructure (LocalStack)**
  - `infra-up`: Start docker-compose (base + dev).
  - `infra-down`: Stop containers.
  - `infra-init`: Run terraform apply.

**2. Update GitHub Actions (`.github/workflows/ci.yml`):**
- Update the workflow steps to call the `Makefile` targets.
- Example: Instead of `run: poetry run ruff .`, use `run: make lint`.
- Ensure the `Infra-Validation` job calls `make setup` and `make infra-init`.

**3. Update Pre-commit (`.pre-commit-config.yaml`):**
- Ensure hooks for `ruff`, and `terraform_fmt` are active.
- (Optional) Add a local hook that runs `make test` before pushing to the repository.

**4. Documentation:**
- Add a "Quick Start" section to the `README.md` that lists the primary `make` commands.

**Constraints:**
- Use `.PHONY` for all targets.
- Ensure the `Makefile` uses `@echo` to provide status updates to the user during execution.
- Paths must remain compatible with the `deployment/` and `infrastructure/` folder structure.

**Definition of Done:**
1. Running `make help` displays a categorized list of commands.
2. `make quality` executes all checks successfully.
3. The GitHub Action YAML is simplified, relying on `make` targets for logic.
